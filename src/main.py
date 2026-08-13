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


def fetch_page(url: str, cache_path: str):
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
    entries = []
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

    print(f"catalogue_pages={pages_visited}")
    print(f"discovered={len(entries)}")
    print(f"unique_urls={len(unique_entries)}")

    return unique_entries


def slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-2]


def extract_book(book_url: str, source_page: str) -> dict:
    cache_path = f"cache/book-{slug_from_url(book_url)}.html"
    html, from_cache = fetch_page(book_url, cache_path)

    if not from_cache:
        time.sleep(DELAY)

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
    book_entries = discover_catalogue()

    raw_records = [extract_book(url, source) for url, source in book_entries]
    print(f"detail_pages={len(raw_records)}")

    valid_records, errors = normalize_and_validate(raw_records)

    save_json(valid_records, "output/books.json")
    save_json(errors, "output/errors.json")

    print(f"valid_records={len(valid_records)}")
    print(f"invalid_records={len(errors)}")