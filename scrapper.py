import argparse
import sys
import json
import datetime
import re
import os
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

def search_python_org(query: str, headless: bool = True, timeout: int = 10, save_json_path: str = None):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get("https://www.python.org/")
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.presence_of_element_located((By.ID, "id-search-field")))
        search_box = driver.find_element(By.ID, "id-search-field")
        search_box.clear()
        search_box.send_keys(query)
        # submit search — send Enter to avoid click-intercepted overlays
        try:
            search_box.send_keys(Keys.RETURN)
        except ElementClickInterceptedException:
            # remove known overlay that blocks clicks/interaction and retry
            driver.execute_script(
                "var el = document.getElementById('fundraiser-banner-host'); if(el && el.parentNode) el.parentNode.removeChild(el);"
            )
            search_box.send_keys(Keys.RETURN)
        # wait for results list
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-recent-events")))
        # capture full rendered page data (before quitting)
        page_snapshot = {
            "url": driver.current_url,
            "title": driver.title,
            "query": query,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "html": driver.page_source,
        }
        if save_json_path:
            try:
                with open(save_json_path, "w", encoding="utf-8") as f:
                    json.dump(page_snapshot, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Failed to save JSON to {save_json_path}: {e}", file=sys.stderr)
        items = driver.find_elements(By.CSS_SELECTOR, "ul.list-recent-events li")
        results = []
        for li in items:
            try:
                a = li.find_element(By.TAG_NAME, "a")
                title = a.text.strip()
                href = a.get_attribute("href")
            except:
                title = ""
                href = ""
            try:
                snippet = li.find_element(By.TAG_NAME, "p").text.strip()
            except:
                snippet = ""
            results.append({"title": title, "url": href, "snippet": snippet})
        return results, page_snapshot
    finally:
        driver.quit()

def main():
    parser = argparse.ArgumentParser(description="Search python.org for a library name and scrape results.")
    parser.add_argument("query", nargs="?", help="Library name or search query")
    parser.add_argument("--no-headless", action="store_true", help="Run browser visible for debugging")
    parser.add_argument("--save-json", action="store_true", help="Save full page snapshot as <query>.json in cwd")
    parser.add_argument("--save-csv", nargs='?', const='search_results.csv', help="Append search metadata+results to CSV file; optional filename")
    args = parser.parse_args()
    query = args.query
    if not query:
        query = input("Library name to search on python.org: ").strip()
        if not query:
            print("No query provided.", file=sys.stderr)
            sys.exit(1)
    save_json_path = None
    if args.save_json:
        # sanitize query to form a safe filename
        sanitized = re.sub(r'[<>:"/\\|?*]', '', query)
        sanitized = sanitized.strip().replace(' ', '_')
        if not sanitized:
            sanitized = 'search_result'
        save_json_path = f"{sanitized}.json"
    results, page_snapshot = search_python_org(query, headless=not args.no_headless, save_json_path=save_json_path)
    if not results:
        print("No results found.")
        return
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']}")
        print(f"   {r['url']}")
        if r['snippet']:
            print(f"   {r['snippet']}")
        print()

    # Append row to CSV if requested
    csv_path = args.save_csv
    if csv_path:
        csv_file = csv_path
        row = {
            'timestamp': page_snapshot.get('timestamp'),
            'query': query,
            'page_url': page_snapshot.get('url'),
            'page_title': page_snapshot.get('title'),
            'results_json': json.dumps(results, ensure_ascii=False),
            'json_snapshot': save_json_path or ''
        }
        write_header = not os.path.exists(csv_file) or os.path.getsize(csv_file) == 0
        try:
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp','query','page_url','page_title','results_json','json_snapshot'])
                if write_header:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            print(f"Failed to write CSV to {csv_file}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()