import heapq, time, hashlib, requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from .helper_functions import normalize_url, score_url
from extractor.extractor import extract_data
from .robots_handler import load_robot_parser, extract_sitemap_urls
from database.database import init_db, upsert_page, insert_link
from indexing.indexer import index_page
# https://unipune.ac.in/../snc/IDS/default.htm
# https://unipune.ac.in/../dept/non_teaching/education_ext/default.htm
# https://unipune.ac.in/../dept/mental_moral_and_social_science/adult_education/default.htm

visited = set()
all_links = set()

def crawl_it(start_url, max_depth):
    main_domain = urlparse(start_url).netloc
    domain = f"{urlparse(start_url).scheme}://{main_domain}"

    rp = load_robot_parser(domain)
    sitemap_urls = extract_sitemap_urls(domain)
    sitemap_urls = set()

    queue = []
    if not sitemap_urls:
        print("No usable sitemap URLs found, falling back to seed URL")

    # Start from sitemap URLs if present
    seed_urls = sitemap_urls or [start_url]

    for url in seed_urls:
        u = normalize_url(url)
        s = score_url(u, 0)
        heapq.heappush(queue, (-s, u, 0))

    # Crawl loop (Priority-based)

    while queue:
        _, url, depth = heapq.heappop(queue)
        url = normalize_url(url)

        if url in visited or depth > max_depth:
            continue

        # Respect robots.txt
        if not rp.can_fetch("*", url):
            print(f"Blocked by robots.txt: {url}")
            continue

        # Fetch
        try:
            time.sleep(1)  # Be polite to servers
            resp = requests.get(url, timeout=6)
            if resp.status_code != 200:
                continue
            if "text/html" not in resp.headers.get("Content-Type", ""):
                print(f"Skipping non-HTML: {url}")
                continue
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        visited.add(url)
        print(f"\nVisited ({len(visited)}): {url}")

        soup = BeautifulSoup(resp.text, 'html.parser')
        title, desc, content = extract_data(soup, url)
        # print(f"title: {title}\ndesc: {desc}\ncontent preview: {content[:150]}\n")

        # Prepare data for DB(prepare hash for the content extracted)
        content_hash = hashlib.sha256(
        content.encode("utf-8", errors="ignore")
        ).hexdigest()

        content_length = len(content)

# storing in DB
        page_id, content_changed, is_new_page = upsert_page(
        url=url,
        domain=main_domain,
        title=title,
        desc=desc,
        content=content,
        content_hash=content_hash,
        content_length=content_length,
        depth=depth,
        status_code=resp.status_code,
        content_type=resp.headers.get("Content-Type", "")
        )   

        if content_changed:
            try:
                # testing 
                print(f"[INDEX] indexing page_id={page_id} url={url}")
  
                index_page(page_id, title, desc, content, is_new_page)
            except Exception as e:
                print(f"Indexing failed for {url}: {e}")

        # Extract internal links
        for link in soup.find_all("a", href=True):
            next_url = urljoin(url, link.get("href"))
            next_url = normalize_url(next_url)

            if urlparse(next_url).netloc != main_domain:
                continue

            if any(next_url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.doc', '.zip', '.mp4', '.css', '.js']):
                continue
            
            # url is crawlable so store in DB

            child_page_id, _, _ = upsert_page(
            url=next_url,
            domain=main_domain,
            title=None,
            desc=None,
            content="",
            content_hash=None,
            content_length=0,
            depth=depth + 1,
            status_code=None,
            content_type=None
            )

            insert_link(page_id, child_page_id)


            all_links.add(next_url)

            s = score_url(next_url, depth + 1)
            heapq.heappush(queue, (-s, next_url, depth + 1))

def summary():
    print("\n----- Summary -----")
    print(f"Total pages visited: {len(visited)}")
    print(f"Total internal links found: {len(all_links)}")
