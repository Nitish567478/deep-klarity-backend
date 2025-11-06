# backend/scraper.py
import requests
from bs4 import BeautifulSoup

USER_AGENT = "ai-quiz-generator/1.0 (+https://example.com)"

def fetch_wikipedia_intro(topic: str) -> str:
    """Fetch the intro paragraph(s) from the Wikipedia page for `topic`."""
    topic_for_url = topic.replace(' ', '_')
    url = f"https://en.wikipedia.org/wiki/{topic_for_url}"
    headers = {"User-Agent": USER_AGENT}

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    content = soup.find(id="mw-content-text")
    if not content:
        raise RuntimeError("Could not find Wikipedia content")

    paras = []
    for p in content.select('p'):
        text = p.get_text(strip=True)
        if text:
            paras.append(text)
        if len(' '.join(paras)) > 1000:
            break

    return '\n\n'.join(paras) if paras else ''
