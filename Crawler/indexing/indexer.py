import re
from collections import Counter
from database.database import get_connection, release_connection


STOPWORDS = {
    "the", "is", "a", "an", "of", "to", "in", "on",
    "for", "and", "or", "with", "as", "by", "at",
    "from", "that", "this", "it", "be", "are"
}

def preprocess_text(title, description, content):
    """
    Returns a Counter: {term: frequency}
    Applies weighting:
      title x3, description x2, content x1
    """
    parts = []

    if title:
        parts.append((title + " ") * 3)
    if description:
        parts.append((description + " ") * 2)
    if content:
        parts.append(content)

    full_text = " ".join(parts).lower()

    # remove punctuation & numbers
    full_text = re.sub(r"[^a-z\s]", " ", full_text)

    tokens = full_text.split()

    filtered = [
        t for t in tokens
        if len(t) >= 2 and t not in STOPWORDS
    ]

    return Counter(filtered)


# helper functions for incremental indexing
def fetch_old_terms(conn, page_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.term
        FROM postings p
        JOIN terms t ON p.term_id = t.id
        WHERE p.page_id = %s
    """, (page_id,))
    rows = cur.fetchall()
    # rows are (id, term) -> map term -> id
    return {term: tid for (tid, term) in rows}


def ensure_term_and_increment(conn, term):
    """Ensure term exists and increment doc_freq by 1; return term_id."""
    cur = conn.cursor()
    # Try to insert as a new term with doc_freq = 1
    cur.execute("""
        INSERT INTO terms (term, doc_freq)
        VALUES (%s, %s)
        ON CONFLICT (term) DO NOTHING
        RETURNING id
    """, (term, 1))
    row = cur.fetchone()
    if row:
        return row[0]

    # If already exists, increment doc_freq and return id
    cur.execute("""
        UPDATE terms
        SET doc_freq = doc_freq + 1
        WHERE term = %s
        RETURNING id
    """, (term,))
    return cur.fetchone()[0]


def decrement_doc_freq_by_id(conn, term_id):
    cur = conn.cursor()
    cur.execute("""
        UPDATE terms
        SET doc_freq = GREATEST(doc_freq - 1, 0)
        WHERE id = %s
        RETURNING doc_freq
    """, (term_id,))
    row = cur.fetchone()
    if row and row[0] == 0:
        # cleanup zero-frequency term
        cur.execute("DELETE FROM terms WHERE id = %s", (term_id,))

# helper functions for indexer
def get_or_create_term(conn, term):
    print(f"[INDEXER] inserting/fetching term: {term}")

    cur = conn.cursor()
    # term_id, doc_freq = cur.execute("SELECT id, doc_freq FROM terms WHERE term = %s", (term,))
    # if term_id is not None:
    #     doc_freq = doc_freq + 1
    # else:
    #     doc_freq = 1
    # # Try insert directly (faster than SELECT first)
    # cur.execute("""
    #     INSERT INTO terms (term, doc_freq)
    #     VALUES (%s, %s)
    #     ON CONFLICT (term) DO NOTHING
    #     RETURNING id
    # """, (term, doc_freq))
    cur.execute("""
        INSERT INTO terms (term)
        VALUES (%s)
        ON CONFLICT (term) DO NOTHING
        RETURNING id
    """, (term,))
    cur.execute("""UPDATE terms
        SET doc_freq = doc_freq + 1
        WHERE term = %s;""", (term,))
    
    row = cur.fetchone()

    if row:
        return row[0]

    # If already exists, fetch it
    cur.execute(
        "SELECT id FROM terms WHERE term = %s",
        (term,)
    )
    return cur.fetchone()[0]

# def get_or_create_term(conn, term):
#     print(f"[INDEXER] inserting/fetching term: {term}")
#     cur = conn.cursor()

#     # 1. Fetch existing term info safely
#     cur.execute("SELECT id, doc_freq FROM terms WHERE term = %s", (term,))
#     row = cur.fetchone()

#     if row is not None:
#         term_id, doc_freq = row[0], row[1]
#         doc_freq = doc_freq + 1
        
#         # 2. If it exists, we must UPDATE the frequency in the database
#         cur.execute(
#             "UPDATE terms SET doc_freq = %s WHERE id = %s",
#             (doc_freq, term_id)
#         )
#         conn.commit()  # Save changes to the database
#         cur.close()
#         return term_id
#     else:
#         doc_freq = 1
#         # 3. If it doesn't exist, INSERT it
#         cur.execute("""
#             INSERT INTO terms (term, doc_freq)
#             VALUES (%s, %s)
#             ON CONFLICT (term) DO NOTHING
#             RETURNING id
#         """, (term, doc_freq))
        
#         insert_row = cur.fetchone()
#         conn.commit()  # Save changes to the database
        
#         if insert_row:
#             cur.close()
#             return insert_row[0]

#         # 4. Fallback if a race condition happened between SELECT and INSERT
#         cur.execute("SELECT id FROM terms WHERE term = %s", (term,))
#         term_id = cur.fetchone()[0]
#         cur.close()
#         return term_id


def upsert_posting(conn, term_id, page_id, freq):
    cur = conn.cursor()
    try :
        cur.execute("""
        INSERT INTO postings (term_id, page_id, frequency)
        VALUES (%s, %s, %s)
        ON CONFLICT (term_id, page_id) DO UPDATE
        SET frequency = EXCLUDED.frequency
    """, (term_id, page_id, freq))
    except Exception as e:
        print(f"Error in upsert_posting: {e}")
        raise
    # testing
    print(f"[INDEXER] upserted posting: term_id={term_id} page_id={page_id}")

    # conn.commit()

# main function to index a page
def index_page(page_id, title, description, content):
    conn = get_connection()

    try:
        # compute new terms + frequencies
        term_freqs = preprocess_text(title, description, content)

        print(f"[INDEXER] tokens count = {len(term_freqs)}")

        cur = conn.cursor()
        # serialize indexing for this page to avoid races
        try:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (page_id,))
        except Exception:
            # advisory locks are Postgres-specific; ignore if not available
            pass

        # fetch old terms present for this page (term -> term_id)
        old_terms = fetch_old_terms(conn, page_id)

        new_terms_set = set(term_freqs.keys())
        old_terms_set = set(old_terms.keys())

        added_terms = new_terms_set - old_terms_set
        removed_terms = old_terms_set - new_terms_set

        # map term -> term_id for inserting postings
        term_id_map = {}

        # handle added terms: create if needed and increment doc_freq
        for term in added_terms:
            tid = ensure_term_and_increment(conn, term)
            term_id_map[term] = tid

        # existing terms keep their ids
        for term in (new_terms_set & old_terms_set):
            term_id_map[term] = old_terms[term]

        # handle removed terms: decrement doc_freq
        for term in removed_terms:
            tid = old_terms[term]
            decrement_doc_freq_by_id(conn, tid)

        # replace postings for the page
        cur.execute("DELETE FROM postings WHERE page_id = %s", (page_id,))

        for term, freq in term_freqs.items():
            term_id = term_id_map.get(term)
            if term_id is None:
                # safety: ensure term exists and increment (shouldn't happen)
                term_id = ensure_term_and_increment(conn, term)
            cur.execute(
                "INSERT INTO postings (term_id, page_id, frequency) VALUES (%s, %s, %s)",
                (term_id, page_id, freq)
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
