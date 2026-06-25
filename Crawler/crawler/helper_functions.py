from urllib.parse import urlparse
def isdomain(url, domain) :
    w1 =  url.split("//")
    w2 = w1[1]
    w3 = w2.split("/")
    newDomain = w3[0]
    if(newDomain == domain) :
        return True
    else :
        return False

def giveDomain(url) :
    w1 =  url.split("//")
    w2 = w1[1]
    w3 = w2.split("/")
    domain = w3[0]
    return domain

    #A URL's syntax: protocol://domain/path?query#fragmen

def normalize_url(url):
    """Clean URL: remove trailing slash, keep root '/' """
    parsed = urlparse(url)

    scheme = parsed.scheme.lower() or "http"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return f"{scheme}://{netloc}{path}"

def score_url(url, depth):
    """Higher score = more important. Priority queue uses negative score."""
    score = 0

    # 1. Depth priority (shallower = better)
    score += max(0, 6 - depth)

    # 2. Important sections 
    important = ["about", "docs", "blog", "download", "help", "tutorial", "news", "product", "service", "research", "community", "forum", "support", "career", "press", "media", "event", "feature", "update", "insight", "analysis", "report", "whitepaper", "case-study"]
    if any(k in url.lower() for k in important):
        score += 4

    # 3. Bad/useless URLs
    ignore = ["login", "signup", "logout", "wp-", "admin", "cart", "checkout","user","account","profile","settings"]
    if any(k in url.lower() for k in ignore):
        score -= 7

    return score
