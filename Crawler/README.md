# 🌐 Web Crawler 

## 📌 Project Overview
This project is an academic implementation of a **domain-specific web crawler integrated with an inverted indexing and search mechanism**, developed as part of the **MSc Computer Science final semester project** at **PUCSD, Savitribai Phule Pune University**.

The system demonstrates the **core working principles of a search engine**, starting from automated web crawling, followed by content extraction, inverted index construction, and keyword-based information retrieval.

---

## 🎯 Objectives
- Crawl web pages starting from a seed URL
- Restrict crawling to a specific domain
- Respect ethical crawling rules using `robots.txt`
- Extract meaningful textual content from HTML pages
- Build an **inverted index** for fast keyword-based search
- Demonstrate the complete **crawler → indexer → search** pipeline

---

## 🧠 System Architecture
```
Crawler → Extractor → Inverted Index → Search Engine
```

---

## ⚙️ Features

### Web Crawling
- Iterative, queue-based crawling
- Depth-limited traversal
- Domain-specific crawling
- Duplicate URL avoidance
- Skips non-HTML resources

### Ethical Crawling
- robots.txt compliance
- Sitemap parsing (when available)

### Content Extraction
- Page title extraction
- Meta description extraction
- Main visible text extraction

### Inverted Indexing
- Tokenizes extracted text
- Maps keywords to document URLs
- Enables fast keyword-based search

### Search Engine
- Keyword-based querying
- Efficient lookup using inverted index

---

## 🛠️ Technologies Used
- Python 3.x
- Requests
- BeautifulSoup
- urllib.robotparser
- heapq
- Linux (Debian-based)

---


---

## ▶️ How to Run
```bash
git clone https://github.com/AdityaDipakTate/web-crawler.git
cd web-crawler
pip install requests beautifulsoup4
```
-Provide a seed (starting) URL in crawler.py then,
```bash 
python3 crawler.py
```

---

## 🚧 Limitations
- No JavaScript-rendered pages
- No ranking algorithms
- Single-threaded crawler

---

## 🔮 Future Enhancements
- TF-IDF and ranking
- JavaScript rendering support
- Database-backed indexing
- Web-based search interface

---

## 🎓 Academic Context
- MSc Computer Science (Final Year)
- PUCSD, Savitribai Phule Pune University

---

## 👤 Author
**Aditya Dipak Tate**  
GitHub: https://github.com/AdityaDipakTate
