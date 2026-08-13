import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator
from typing import Optional

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/IgnacioLegui/polite-scraper)"
TIMEOUT = 10
DELAY = 0.5
MAX_CATALOGUE_PAGES = 3
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

# Toggle to True once to prove Stage 5 survives a broken page,
# then set back to False for the real run.
INJECT_FAKE_URL = False
FAKE_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html"

stats = {"pages_fetched": 0, "cache_hits": 0, "failed_pages": []}


def fetch_page(url: str, cache_path: str):
    """Fetch a page, reading from cache if present. Retries once on
    timeout/5xx. Does NOT retry on 404/403. Raises on final failure."""
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        stats["cache_hits"] += 1
        print(f"CACHE HIT — {cache_path} ({len(html)} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    max_attempts = 2  # one try + one retry, only for timeout/5xx
    attempts = 0

    while True:
        attempts += 1
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            if attempts < max_attempts:
                print(f"TIMEOUT — {url} (attempt {attempts}), retrying...")
                time.sleep(1)
                continue
            raise RuntimeError(f"Fetch failed after retry: {url} timed out")

        if response.status_code == 200:
            break
        elif response.status_code in (404, 403):
            raise RuntimeError(f"Fetch failed: {url} returned status {response.status_code}")
        elif response.status_code >= 500 and attempts < max_attempts:
            print(f"SERVER ERROR {response.status_code} — {url} (attempt {attempts}), retrying...")
            time.sleep(1)
            continue
        else:
            raise RuntimeError(f"Fetch failed: {url} returned status {response.status_code}")

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    stats["pages_fetched"] += 1
    print(f"FETCH — {url} -> {cache_path} ({len(response.text)} bytes)")
    time.sleep(DELAY)
    return response.text


def discover_catalogue():
    entries = []
    current_url = START_URL
    pages_visited = 0

    while current_url and pages_visited < MAX_CATALOGUE_PAGES:
        pages_visited += 1
        cache_path = f"cache/catalogue-page-{pages_visited}.html"
        html = fetch_page(current_url, cache_path)
        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):
            href = article.h3.a["href"]
            book_url = urljoin(current_url, href)
            entries.append((book_url, current_url))

        next_link = soup.select_one("li.next a")
        if next_link and pages_visited < MAX_CATALOGUE_PAGES:
            current_url = urljoin(current_url, next_link["href"])
        else:
            current_url = None

    seen = set()
    unique_entries = []
    for book_url, source_page in entries:
        if book_url not in seen:
            seen.add(book_url)
            unique_entries.append((book_url, source_page))

    if INJECT_FAKE_URL:
        unique_entries.append((FAKE_URL, START_URL))
        print(f"[TEST] injected fake URL: {FAKE_URL}")

    print(f"catalogue_pages={pages_visited}")
    print(f"discovered={len(entries)}")
    print(f"unique_urls={len(unique_entries)}")
    return unique_entries


def slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-2]


def extract_book(book_url: str, source_page: str):
    """Returns a raw record dict, or None if this page failed
    (logged into stats['failed_pages'])."""
    cache_path = f"cache/book-{slug_from_url(book_url)}.html"

    try:
        html = fetch_page(book_url, cache_path)
    except Exception as exc:
        print(f"SKIPPED — {book_url} ({exc})")
        stats["failed_pages"].append({"url": book_url, "reason": str(exc)})
        return None

    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one("div.product_main h1").get_text(strip=True)
    price_text = soup.select_one("p.price_color").get_text(strip=True)
    availability_text = " ".join(
        soup.select_one("p.instock.availability").get_text().split()
    )

    rating_tag = soup.select_one("p.star-rating")
    rating_classes = rating_tag["class"] if rating_tag else []
    rating_text = rating_classes[1] if len(rating_classes) > 1 else None

    desc_tag = soup.select_one("#product_description ~ p")
    description = desc_tag.get_text(strip=True) if desc_tag else None

    return {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def parse_price_gbp(price_text: str) -> float:
    match = re.search(r"[\d.]+", price_text)
    if not match:
        raise ValueError(f"could not parse a number out of price_text={price_text!r}")
    return float(match.group())


class BookRecord(BaseModel):
    title: str
    product_url: str
    price_gbp: float
    price_text: str
    availability_text: str
    rating_text: Optional[str] = None
    description: Optional[str] = None
    source_page: str
    fetched_at: str

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_https(cls, v):
        if not v.startswith("https://"):
            raise ValueError("must start with https://")
        return v

    @field_validator("price_gbp")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("price_gbp must be a positive number")
        return v


def normalize_and_validate(raw_records: list[dict]):
    valid_records = []
    errors = []
    for raw in raw_records:
        try:
            price_gbp = parse_price_gbp(raw["price_text"])
            candidate = {**raw, "price_gbp": price_gbp}
            record = BookRecord(**candidate)
            valid_records.append(record.model_dump())
        except Exception as exc:
            errors.append({"product_url": raw.get("product_url"), "reason": str(exc)})
    return valid_records, errors


def save_json(data, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    run_start = time.time()
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    book_entries = discover_catalogue()

    raw_records = []
    for book_url, source_page in book_entries:
        record = extract_book(book_url, source_page)
        if record is not None:
            raw_records.append(record)

    print(f"detail_pages={len(raw_records)}")

    valid_records, errors = normalize_and_validate(raw_records)
    save_json(valid_records, "output/books.json")
    save_json(errors, "output/errors.json")

    duration_seconds = round(time.time() - run_start, 2)
    run_report = {
        "started_at": started_at,
        "duration_seconds": duration_seconds,
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": len(valid_records),
        "invalid_records": len(errors),
        "failed_pages": len(stats["failed_pages"]),
        "failed_page_details": stats["failed_pages"],
    }
    save_json(run_report, "output/run-report.json")

    print(f"valid_records={len(valid_records)}")
    print(f"invalid_records={len(errors)}")
    print(f"failed_pages={len(stats['failed_pages'])}")