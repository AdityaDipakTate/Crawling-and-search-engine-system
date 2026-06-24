def extract_data(soup, url):
    title = soup.title.string.strip() if soup.title else None

    meta = soup.find("meta", attrs={"name": "description"})

    desc = meta["content"].strip() if meta and meta.get("content") else None
    

    # paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
    # content = " ".join(paragraphs[:20])

        # Remove noise tags first
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Get text from p, div, li, span — much broader
    tags = soup.find_all(["p", "div", "li", "article", "section"])
    seen = set()
    parts = []
    for tag in tags:
        text = tag.get_text(separator=" ", strip=True)
        if len(text) > 40 and text not in seen:  # skip tiny fragments
            seen.add(text)
            parts.append(text)
        if len(parts) >= 50:
            break

    content = " ".join(parts)
    return title, desc, content
