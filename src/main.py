import os
import requests

CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_PATH = "cache/catalogue-page-1.html"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/IgnacioLegui/polite-scraper)"
TIMEOUT = 10  # seconds


def fetch_page(url: str, cache_path: str) -> str:
    """Fetch a page, reading from the local cache if it already exists."""
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT — {cache_path} ({len(html)} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed: {url} returned status {response.status_code}")

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"FETCH — {url} -> {cache_path} ({len(response.text)} bytes)")
    return response.text


if __name__ == "__main__":
    fetch_page(CATALOGUE_URL, CACHE_PATH)