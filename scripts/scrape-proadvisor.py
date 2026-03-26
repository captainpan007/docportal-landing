"""
Scrape QuickBooks ProAdvisor directory for bookkeeper leads.

Uses Playwright with full anti-detection config.

Usage:
    python scripts/scrape-proadvisor.py

Requires:
    pip install playwright
    playwright install chromium
"""

import asyncio
import csv
import json
import random
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PwTimeout

# ── Config ──────────────────────────────────────────────────────────
BASE_URL = "https://proadvisor.intuit.com/app/accountant/search"
CITIES = [
    "New York, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Houston, TX",
    "Phoenix, AZ",
    "Philadelphia, PA",
    "San Antonio, TX",
    "San Diego, CA",
    "Dallas, TX",
    "Austin, TX",
]
DELAY_MIN = 8
DELAY_MAX = 15

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CSV_PATH = DATA_DIR / "proadvisor_leads.csv"
PROGRESS_PATH = DATA_DIR / "scrape_progress.json"
CSV_FIELDS = ["search_id", "name", "email", "city", "website"]


# ── Helpers ─────────────────────────────────────────────────────────
async def random_delay():
    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    return {"scraped_ids": [], "done_cities": []}


def save_progress(progress: dict):
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def append_to_csv(row: dict):
    file_exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ── Browser setup with anti-detection ───────────────────────────────
async def create_browser(pw):
    browser = await pw.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--window-size=1280,800",
        ],
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
        timezone_id="America/New_York",
    )
    page = await context.new_page()

    # Anti-detection: must run before any page load
    await page.add_init_script("""
        // Hide webdriver flag
        Object.defineProperty(navigator, 'webdriver', {get: () => false});
        // Fake real plugins
        Object.defineProperty(navigator, 'plugins', {get: () => [
            {name: 'Chrome PDF Plugin'}, {name: 'Chrome PDF Viewer'},
            {name: 'Native Client'}, {name: 'Widevine'}, {name: 'ChromeOS'}
        ]});
        // Add chrome object
        window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};
        // Fake languages
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    """)

    return browser, context, page


# ── Search ID collection ────────────────────────────────────────────
async def collect_search_ids_for_city(page, city: str) -> list[str]:
    location = city.replace(" ", "+").replace(",", "%2C")
    url = f"{BASE_URL}?region=US&ub=c&location={location}"

    print(f"  Navigating: {url}")
    await page.goto(url, wait_until="domcontentloaded")

    # Wait for React to render
    print(f"  Waiting 6s for SPA render...")
    await page.wait_for_timeout(6000)

    # Debug
    title = await page.title()
    print(f"  [DEBUG] Page title: {title}")
    print(f"  [DEBUG] Current URL: {page.url}")

    links = await page.query_selector_all('a[href*="searchId"]')
    print(f"  [DEBUG] Found {len(links)} a[href*='searchId'] links")

    if len(links) == 0:
        text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
        print(f"  [DEBUG] Page text (first 500 chars):")
        print(f"  {text}")
        return []

    # Print first 3
    for i, link in enumerate(links[:3]):
        href = await link.get_attribute("href")
        print(f"  [DEBUG]   [{i+1}] {href}")

    # Infinite scroll — stop after 3 consecutive scrolls with no new links
    prev_count = len(links)
    stale_scrolls = 0
    while stale_scrolls < 3:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)
        links = await page.query_selector_all('a[href*="searchId"]')
        current_count = len(links)
        if current_count == prev_count:
            stale_scrolls += 1
        else:
            stale_scrolls = 0
            print(f"  Scrolling... {current_count} links loaded")
            prev_count = current_count

    # Extract unique IDs
    search_ids = await page.evaluate("""() => {
        const ids = new Set();
        document.querySelectorAll('a[href*="searchId"]').forEach(a => {
            const m = a.href.match(/searchId=([^&]+)/);
            if (m) ids.add(m[1]);
        });
        return [...ids];
    }""")
    print(f"  Found {len(search_ids)} unique searchIds for {city}")
    return search_ids


# ── Detail page scraping ────────────────────────────────────────────
async def scrape_detail_page(page, search_id: str) -> dict | None:
    url = f"{BASE_URL}?searchId={search_id}"

    try:
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(6000)
    except PwTimeout:
        print("timeout")
        return None

    # Check for CAPTCHA
    captcha = await page.query_selector(
        'iframe[src*="recaptcha"], .g-recaptcha, [class*="captcha"]'
    )
    if captcha:
        print(f"\n⚠️  CAPTCHA detected! Please solve it in the browser window, then press Enter to continue...")
        await asyncio.get_event_loop().run_in_executor(None, input)
        await page.wait_for_timeout(2000)

    detail = await page.evaluate("""() => {
        const getText = (sels) => {
            for (const s of sels) {
                const el = document.querySelector(s);
                if (el && el.textContent.trim()) return el.textContent.trim();
            }
            return '';
        };

        const name = getText(['h1', '[class*="name" i]', '[data-testid*="name"]']);
        const city = getText(['[class*="location" i]', '[class*="address" i]', '[class*="city" i]']);

        let email = '';
        const mailto = document.querySelector('a[href^="mailto:"]');
        if (mailto) email = mailto.href.replace('mailto:', '').split('?')[0];
        if (!email) {
            const m = document.body.innerText.match(
                /[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}/
            );
            if (m) email = m[0];
        }

        let website = '';
        for (const a of document.querySelectorAll('a[href]')) {
            const h = a.href || '';
            if (h.startsWith('http') &&
                !h.includes('intuit.com') && !h.includes('quickbooks') &&
                !h.includes('google') && !h.includes('facebook') &&
                !h.includes('linkedin') && !h.includes('twitter') && !h.includes('yelp')) {
                website = h;
                break;
            }
        }

        return { name, city, email, website };
    }""")

    email = detail.get("email", "").strip()
    if not email or "@" not in email:
        return None

    return {
        "search_id": search_id,
        "name": detail.get("name", "").strip(),
        "email": email,
        "city": detail.get("city", "").strip(),
        "website": detail.get("website", "").strip(),
    }


# ── Main ────────────────────────────────────────────────────────────
async def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    progress = load_progress()
    scraped_ids = set(progress["scraped_ids"])
    done_cities = set(progress["done_cities"])

    print(f"Resuming: {len(scraped_ids)} IDs scraped, {len(done_cities)} cities done\n")

    async with async_playwright() as pw:
        browser, context, page = await create_browser(pw)
        total_new = 0

        for city in CITIES:
            if city in done_cities:
                print(f"\nSkipping {city} (already done)")
                continue

            print(f"\n{'='*50}")
            print(f"City: {city}")
            print(f"{'='*50}")

            try:
                search_ids = await collect_search_ids_for_city(page, city)
            except Exception as e:
                print(f"  Error: {e}")
                continue

            new_ids = [sid for sid in search_ids if sid not in scraped_ids]
            print(f"  {len(new_ids)} new / {len(search_ids)} total")

            for i, sid in enumerate(new_ids, 1):
                print(f"  [{i}/{len(new_ids)}] {sid}...", end=" ")
                try:
                    lead = await scrape_detail_page(page, sid)
                except Exception as e:
                    print(f"error: {e}")
                    lead = None

                scraped_ids.add(sid)
                if lead:
                    append_to_csv(lead)
                    total_new += 1
                    print(f"OK - {lead['name']} ({lead['email']})")
                else:
                    print("skipped (no email)")

                progress["scraped_ids"] = list(scraped_ids)
                save_progress(progress)
                await random_delay()

            city_leads = sum(1 for sid in new_ids if sid in scraped_ids)
            print(f"\n  City done: {city} — {len(search_ids)} profiles found, {total_new} leads with email so far")

            if search_ids:
                done_cities.add(city)
            else:
                print(f"  0 results, will retry next run")
            progress["done_cities"] = list(done_cities)
            save_progress(progress)

        await context.close()
        await browser.close()

    print(f"\nDone! {total_new} new leads saved to {CSV_PATH}")
    print(f"Total scraped IDs: {len(scraped_ids)}")


if __name__ == "__main__":
    asyncio.run(main())
