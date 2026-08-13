import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/IgnacioLegui/polite-scraper)"
TIMEOUT = 10
DELAY = 0.5  # seconds between real (non-cached) requests
MAX_CATALOGUE_PAGES = 3
START_URL = "https://books.toscrape.com/catalogue/page-1.html"


def fetch_page(url: str, cache_path: str):
    """Fetch a page, reading from the local cache if it already exists.
    Returns (html, from_cache)."""
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT — {cache_path} ({len(html)} bytes)")
        return html, True

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed: {url} returned status {response.status_code}")

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"FETCH — {url} -> {cache_path} ({len(response.text)} bytes)")
    return response.text, False


def discover_catalogue():
    """Walk the catalogue's own 'next' links for up to MAX_CATALOGUE_PAGES,
    collecting every book URL along the way."""
    book_urls = []
    current_url = START_URL
    pages_visited = 0

    while current_url and pages_visited < MAX_CATALOGUE_PAGES:
        pages_visited += 1
        cache_path = f"cache/catalogue-page-{pages_visited}.html"
        html, from_cache = fetch_page(current_url, cache_path)

        if not from_cache:
            time.sleep(DELAY)

        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):
            href = article.h3.a["href"]
            book_urls.append(urljoin(current_url, href))

        next_link = soup.select_one("li.next a")
        if next_link and pages_visited < MAX_CATALOGUE_PAGES:
            current_url = urljoin(current_url, next_link["href"])
        else:
            current_url = None

    unique_urls = list(dict.fromkeys(book_urls))  # de-dupe, keep order

    print(f"catalogue_pages={pages_visited}")
    print(f"discovered={len(book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls


if __name__ == "__main__":
    discover_catalogue()