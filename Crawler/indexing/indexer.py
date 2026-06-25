import re
from collections import Counter
from database.database import (
    delete_page_postings,
    decrement_doc_freq,
    get_connection,
    get_page_terms,
    increment_doc_freq,
    release_connection,
)


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


# helper functions for indexer
def get_or_create_term(conn, term):

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO terms (term, doc_freq)
        VALUES (%s, 0)
        ON CONFLICT (term) DO NOTHING
        RETURNING id
    """, (term,))

    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute(
        "SELECT id FROM terms WHERE term = %s",
        (term,)
    )

    return cur.fetchone()[0]

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
def index_page(page_id, title, description, content, is_new_page):
    conn = get_connection()

    try:
        # compute new terms + frequencies
        term_freqs = preprocess_text(title, description, content)
        new_terms = set(term_freqs.keys())

        print(f"[INDEXER] tokens count = {len(term_freqs)}")

        cur = conn.cursor()
        # serialize indexing for this page to avoid races
        try:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (page_id,))
        except Exception:
            # advisory locks are Postgres-specific; ignore if not available
            pass

        old_terms = set() if is_new_page else get_page_terms(conn, page_id)

        added_terms = new_terms - old_terms
        removed_terms = old_terms - new_terms

        # map term -> term_id for inserting postings
        term_id_map = {}

        # Ensure terms exist before any doc_freq updates.
        for term in new_terms:
            term_id_map[term] = get_or_create_term(conn, term)

        for term in added_terms:
            increment_doc_freq(conn, term)
        for term in removed_terms:
            decrement_doc_freq(conn, term)

        # replace postings for the page
        delete_page_postings(conn, page_id)

        for term, freq in term_freqs.items():
            cur.execute(
                "INSERT INTO postings (term_id, page_id, frequency) VALUES (%s, %s, %s)",
                (term_id_map[term], page_id, freq)
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
