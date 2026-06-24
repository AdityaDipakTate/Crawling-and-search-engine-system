import psycopg2
from psycopg2 import pool
from datetime import datetime

# Connection
# def get_connection():
#     return psycopg2.connect(
#         dbname="crawler_db",
#         user="crawler_user",
#         password="strongpassword",
#         host="localhost",
#         port="5432"
#     )   

# database.py

_pool = None

def init_pool():
    global _pool
    _pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dbname="crawler_db",
        user="crawler_user",
        password="strongpassword",
        host="localhost",
        port="5432"
    )

def get_connection():
    return _pool.getconn()

def release_connection(conn):
    _pool.putconn(conn)

# Initialize DB
def init_db():
    init_pool()
    conn = get_connection()
    try:
        cur = conn.cursor()

        # pages table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
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

            crawled_at TIMESTAMP,
            crawl_count INTEGER DEFAULT 1
        )
        """)

        # links table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS links (
            from_page INTEGER REFERENCES pages(id),
            to_page INTEGER REFERENCES pages(id),
            PRIMARY KEY (from_page, to_page)
        )
        """)

        # terms table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS terms (
            id SERIAL PRIMARY KEY,
            term TEXT UNIQUE,
            doc_freq INTEGER DEFAULT 0  
        )
        """)

        # postings table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS postings (
            term_id INTEGER REFERENCES terms(id),
            page_id INTEGER REFERENCES pages(id),
            frequency INTEGER,
            PRIMARY KEY (term_id, page_id)
        )
        """)

        conn.commit()
    finally:
        release_connection(conn)


# UPSERT PAGE
def upsert_page(
    url, domain, title, desc, content,
    content_hash, content_length,
    depth, status_code, content_type
):
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Check if page exists
        cur.execute(
            "SELECT id, content_hash FROM pages WHERE url = %s",
            (url,)
        )
        row = cur.fetchone()

        content_changed = False
        now = datetime.utcnow()

        if row is None:
            # INSERT new page
            cur.execute("""
            INSERT INTO pages (
                url, domain, title, description, content,
                content_hash, content_length,
                depth, status_code, content_type,
                crawled_at, crawl_count
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            RETURNING id
            """, (
                url, domain, title, desc, content,
                content_hash, content_length,
                depth, status_code, content_type,
                now
            ))

            page_id = cur.fetchone()[0]
            content_changed = content_hash is not None

        else:
            page_id, old_hash = row

            if content_hash is None:
                pass

            elif old_hash == content_hash:
                # metadata update
                cur.execute("""
                UPDATE pages
                SET crawl_count = crawl_count + 1,
                    status_code = %s,
                    content_type = %s,
                    crawled_at = %s
                WHERE id = %s
                """, (status_code, content_type, now, page_id))

            else:
                # full update
                cur.execute("""
                UPDATE pages
                SET title = %s,
                    description = %s,
                    content = %s,
                    content_hash = %s,
                    content_length = %s,
                    crawl_count = crawl_count + 1,
                    status_code = %s,
                    content_type = %s,
                    crawled_at = %s
                WHERE id = %s
                """, (
                    title, desc, content,
                    content_hash, content_length,
                    status_code, content_type,
                    now, page_id
                ))

                content_changed = True

        conn.commit()

        print(
            f"[DB] url={url} | "
            f"hash={'None' if content_hash is None else 'REAL'} | "
            f"content_changed={content_changed}"
        )

        return page_id, content_changed
    finally:
        release_connection(conn)#?


# Utility
def page_exists(url):
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pages WHERE url = %s", (url,))
        exists = cur.fetchone() is not None

        return exists
    finally:
        release_connection(conn)


# Insert link
def insert_link(from_page_id, to_page_id):
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO links (from_page, to_page)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        """, (from_page_id, to_page_id))

        conn.commit()
    finally:
        release_connection(conn)