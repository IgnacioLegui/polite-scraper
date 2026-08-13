# Polite Scraper

## Target classification
- **Site:** Books to Scrape (books.toscrape.com)
- **Why:** it's an explicit sandbox built for practicing web scraping —
  toscrape.com describes it as a fictional bookstore meant to be scraped,
  safe for beginners.
- **Scope:** first 3 catalogue pages only (~60 books).
- **Data collected:** title, product URL, price, availability, rating,
  description, source page, fetch timestamp — no personal or account data.
- **robots.txt result:** requested https://books.toscrape.com/robots.txt —
  returns 404, no robots file found. A missing file is not permission by
  itself, but the site's own description above is.

I will not reuse this code on another site without checking its rules and terms first.

## How to run
```
git clone https://github.com/IgnacioLegui/polite-scraper.git
cd polite-scraper
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\main.py
```
Output: `output/books.json` (60 validated records) and `output/run-report.json`.

## Lane
Python 3.10+, using `requests`, `beautifulsoup4`, and `pydantic`. Dependencies pinned in `requirements.txt`.

## Record schema
- `title` (string)
- `product_url` (string, https, canonical identity)
- `price_gbp` (number)
- `price_text` (string, original)
- `availability_text` (string)
- `rating_text` (string or null)
- `description` (string or null)
- `source_page` (string, https)
- `fetched_at` (string, ISO 8601 UTC)

## Politeness rules
- Custom User-Agent (`FlyRankInternshipA9/1.0`) naming the project and linking to this repo.
- 10-second timeout on every request — never waits forever.
- At least 0.5s between real requests; cached pages need no delay.
- Checks the HTTP status code before parsing anything; only 200 is treated as a real page.
- Caches every fetched page to `cache/`, so development never re-asks the site.

## Run report (sample)
```json
{
  "started_at": "2026-08-13T20:05:11Z",
  "duration_seconds": 0.49,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_page_details": []
}
```

No browser was needed for this assignment: all the data (title, price, availability, description) is already present in the HTML the server sends on first request — a browser would only add cost (memory, startup time) without unlocking anything that wasn't already there.

## Known limitation
No automated tests. Every stage was validated by hand against its checkpoint (running the script and checking the printed counts/output files), not with tests that run on their own — a stranger cloning the repo has to trust the README's run instructions, not a green test suite.

## Ethics note
This scraper only touches an explicit, public practice sandbox (Books to Scrape) built for this exact purpose. As a general rule: prefer an official API over scraping whenever one exists, never bypass logins, paywalls, or explicit blocks, and only collect the data actually needed for the task.