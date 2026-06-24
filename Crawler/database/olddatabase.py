import sqlite3
import json
from datetime import datetime

DB_PATH = "crawler.db"
 
# Connection
def get_connection():
    return sqlite3.connect(DB_PATH)

# Initialize DB
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # pages table (upgraded, minimal)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    domain TEXT,

    title TEXT,
    description TEXT,
    content TEXT,

    content_hash TEXT,
    content_length INTEGER,

    depth INTEGER,
    status_code INTEGER,
    content_type TEXT,

    crawled_at TEXT,
    crawl_count INTEGER DEFAULT 1
    )
    """)


    # links table (NEW)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS links (
        from_page INTEGER,
        to_page INTEGER,

        UNIQUE(from_page, to_page),

        FOREIGN KEY(from_page) REFERENCES pages(id),
        FOREIGN KEY(to_page) REFERENCES pages(id)
    )
    """)

        # terms table (for inverted index)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term TEXT UNIQUE
    )
    """)

    # postings table (term → page mapping)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS postings (
        term_id INTEGER,
        page_id INTEGER,
        frequency INTEGER,

        PRIMARY KEY (term_id, page_id),

        FOREIGN KEY(term_id) REFERENCES terms(id),
        FOREIGN KEY(page_id) REFERENCES pages(id)
    )
    """)

    conn.commit()
    conn.close()

# insert replace with upsert
def upsert_page(
                url, domain, title, desc, content,
                content_hash, content_length,
                depth, status_code, content_type
                ):
    conn = get_connection()
    cur = conn.cursor()

    # Check if page exists
    cur.execute(
        "SELECT id, content_hash FROM pages WHERE url = ?",
        (url,)
    )
    content_changed = False
    row = cur.fetchone()

    now = datetime.utcnow().isoformat()

    if row is None:
        # INSERT new page
        cur.execute("""
        INSERT INTO pages
        (url, domain, title, description, content,
         content_hash, content_length,
         depth, status_code, content_type,
         crawled_at, crawl_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            url, domain, title, desc, content,
            content_hash, content_length,
            depth, status_code, content_type,
            now
        ))
        page_id = cur.lastrowid
        content_changed = content_hash is not None

    else:
        page_id, old_hash = row

        if content_hash is None:
        # placeholder upsert → preserve existing data
            pass

        elif old_hash == content_hash:
            # Content unchanged → metadata update only
            cur.execute("""
            UPDATE pages
            SET crawl_count = crawl_count + 1,
                status_code = ?,
                content_type = ?,
                crawled_at = ?
            WHERE id = ?
            """, (status_code, content_type, now, page_id))

        else:
            # Content changed → full update
            cur.execute("""
            UPDATE pages
            SET title = ?,
                description = ?,
                content = ?,
                content_hash = ?,
                content_length = ?,
                crawl_count = crawl_count + 1,
                status_code = ?,
                content_type = ?,
                crawled_at = ?
            WHERE id = ?
            """, (
                title, desc, content,
                content_hash, content_length,
                status_code, content_type,
                now, page_id
            ))
            content_changed = True

    conn.commit()
    conn.close()

    # testing 
    print(
    f"[DB] url={url} | "
    f"hash={'None' if content_hash is None else 'REAL'} | "
    f"content_changed={content_changed}"
    )

    return page_id, content_changed

# Utility
def page_exists(url):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pages WHERE url = ?", (url,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def insert_link(from_page_id, to_page_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT OR IGNORE INTO links (from_page, to_page)
        VALUES (?, ?)
        """, (from_page_id, to_page_id))
        conn.commit()
    finally:
        conn.close()

