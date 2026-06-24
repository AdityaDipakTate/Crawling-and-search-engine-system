
from crawler.crawler import crawl_it, summary
from database.database import init_db


# import heapq, time, hashlib, requests
# from urllib.parse import urlparse, urljoin
# from bs4 import BeautifulSoup
# from helper_functions import normalize_url,score_url
# from extractor.extractor import extract_data
# from robots_handler import load_robot_parser, extract_sitemap_urls
# # from ..database.database import init_db, upsert_page, insert_link
# from indexing.indexer import index_page
visited = set()
all_links = set()

init_db()
start_url = "https://www.unipune.ac.in/"
# start_url = "https://unipune.ac.in/../dept/mental_moral_and_social_science/adult_education/default.htm"

# start_url = "https://www.thehindu.com/news/national/andhra-pradesh/teachers-body-urges-ap-government-to-clear-35000-crore-in-pending-dues/article70823161.ece"
# start_url = "https://example.com/"
# start_url = "https://www.python.org/"
# start_url = "https://www.python.org/about/apps"
# start_url = "https://flask.palletsprojects.com/"
crawl_it(start_url, 1)
summary()



