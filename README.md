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