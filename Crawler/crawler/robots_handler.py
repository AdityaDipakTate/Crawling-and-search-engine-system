import urllib.robotparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def load_robot_parser(domain):
    """
    Load and parse robots.txt for the given domain.
    Returns a robotparser object (to check crawl permissions).
    """
    robots_url = urljoin(domain, "/robots.txt")
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        print(f" Loaded robots.txt: {robots_url}")
    except Exception as e:
        print(f" Could not load robots.txt ({e})")
    return rp


def extract_sitemap_urls(domain):
    """
    Attempts to extract sitemap URLs from robots.txt,
    and then parse sitemap.xml to collect page URLs.
    """
    sitemap_urls = set()
    try:
        robots_url = urljoin(domain, "/robots.txt")
        resp = requests.get(robots_url, timeout=5)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap_link = line.split(":", 1)[1].strip()
                    sitemap_urls.update(parse_sitemap(sitemap_link))
    except Exception as e:
        print(" ")
    return sitemap_urls


def parse_sitemap(sitemap_url):
    """
    Parse a given sitemap.xml and return all URLs inside it.
        # print(f" Failed to fetch sitemap from robots.txt: {e}")
    """
    urls = set()
    try:
        resp = requests.get(sitemap_url, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "xml")
            for loc in soup.find_all("loc"):
                urls.add(loc.text.strip())
            print(f" Found {len(urls)} URLs from sitemap: {sitemap_url}")
    except Exception as e:
        print(f" Could not parse sitemap ({sitemap_url}): {e}")
    return urls
