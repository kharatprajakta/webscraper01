import os
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import argparse
import requests
import webbrowser
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument('--disable-dev-shm-usage')
    # set a common desktop user-agent to avoid bot-only responses
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def fetch_image_urls(query, max_links, driver, sleep_between_interactions=1.0):
    # Default was Google Images; keep for backwards compatibility but
    # prefer Pinterest via fetch_image_urls_pinterest below. This function
    # remains as a Google Images scraper if called directly.
    search_url = "https://www.google.com/search?tbm=isch&q={}".format(quote(query))
    driver.get(search_url)
    image_urls = set()
    thumbnails_selector = "img.Q4LuWd"
    last_height = driver.execute_script("return document.body.scrollHeight")

    # try to close cookie/consent dialogs that block interaction
    try:
        buttons = driver.find_elements(By.XPATH, "//button|//div[@role='button']")
        for b in buttons:
            try:
                txt = (b.text or "").lower()
                if any(x in txt for x in ("accept", "agree", "i agree", "allow all", "consent")):
                    b.click()
                    time.sleep(1)
                    break
            except Exception:
                continue
    except Exception:
        pass

    wait = WebDriverWait(driver, 10)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, thumbnails_selector)))
    except Exception:
        # no thumbnails found within timeout
        return []

    while len(image_urls) < max_links:
        thumbnails = driver.find_elements(By.CSS_SELECTOR, thumbnails_selector)
        for img in thumbnails:
            if len(image_urls) >= max_links:
                break
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", img)
                time.sleep(0.2)
                img.click()
            except Exception:
                continue

            try:
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img.n3VNCb")))
            except Exception:
                time.sleep(sleep_between_interactions)

            images = driver.find_elements(By.CSS_SELECTOR, "img.n3VNCb")
            for actual in images:
                src = actual.get_attribute('src')
                if not src:
                    continue
                if src.startswith('http') and not src.startswith('data:'):
                    image_urls.add(src)
                    if len(image_urls) >= max_links:
                        break

        # scroll to load more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_between_interactions)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            try:
                load_more = driver.find_element(By.XPATH, "//input[@type='button' and (@value='Show more results' or contains(@aria-label,'Load more'))]")
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(sleep_between_interactions)
            except Exception:
                break
        last_height = new_height

    return list(image_urls)[:max_links]


def fetch_image_urls_pinterest(query, max_links, driver, sleep_between_interactions=1.0):
    # Pinterest search URL for pins
    search_url = "https://www.pinterest.com/search/pins/?q={}".format(quote(query))
    driver.get(search_url)
    image_urls = set()
    # Helpful selector: Pinterest serves pin images from i.pinimg.com
    pin_img_selector = "img[src*='pinimg.com']"

    # try to close cookie/consent/login prompts
    try:
        buttons = driver.find_elements(By.XPATH, "//button|//div[@role='button']")
        for b in buttons:
            try:
                txt = (b.text or "").lower()
                if any(x in txt for x in ("accept", "agree", "i agree", "allow all", "consent", "close")):
                    b.click()
                    time.sleep(0.5)
            except Exception:
                continue
    except Exception:
        pass

    wait = WebDriverWait(driver, 10)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, pin_img_selector)))
    except Exception:
        return []

    last_height = driver.execute_script("return document.body.scrollHeight")
    while len(image_urls) < max_links:
        imgs = driver.find_elements(By.CSS_SELECTOR, pin_img_selector)
        for img in imgs:
            if len(image_urls) >= max_links:
                break
            try:
                src = img.get_attribute('src') or img.get_attribute('data-src') or img.get_attribute('data-hires')
            except Exception:
                src = None
            if not src:
                continue
            # skip data urls and placeholders
            if src.startswith('http') and 'pinimg.com' in src:
                image_urls.add(src)
        # scroll to load more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_between_interactions)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # nothing more to load
            break
        last_height = new_height

    return list(image_urls)[:max_links]


def download_image(url, dest_folder, idx, timeout=15):
    try:
        resp = requests.get(url, stream=True, timeout=timeout)
        if resp.status_code == 200:
            content_type = resp.headers.get('content-type', '')
            if 'image' in content_type:
                ext = content_type.split('/')[-1].split(';')[0]
            else:
                ext = url.split('.')[-1].split('?')[0][:5]
            filename = f"img_{idx:04d}.{ext}"
            path = os.path.join(dest_folder, filename)
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return path
    except Exception:
        return None


def make_gallery(out_dir, image_paths):
    out = Path(out_dir)
    index_file = out / "index.html"
    lines = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>Image Gallery</title></head><body>",
        f"<h1>Downloaded images ({len(image_paths)})</h1>",
        "<div style='display:flex;flex-wrap:wrap;'>",
    ]
    for p in image_paths:
        rel = Path(p).name
        lines.append(f"<div style='margin:8px'><img src=\"{rel}\" style=\"max-width:240px;max-height:180px;display:block\"><div style='font-size:11px'>{rel}</div></div>")
    lines.append("</div></body></html>")
    index_file.write_text("\n".join(lines), encoding="utf-8")
    try:
        webbrowser.open(index_file.as_uri())
    except Exception:
        print(f"Gallery created at {index_file}")


def main():
    parser = argparse.ArgumentParser(description="Download images from Google Images or Pinterest (Selenium).")
    parser.add_argument('--query', '-q', required=True, help='Search query')
    parser.add_argument('--limit', '-n', type=int, default=20, help='Number of images to download')
    parser.add_argument('--out', '-o', default='images', help='Output folder')
    parser.add_argument('--visible', action='store_true', help='Run Chrome visibly')
    parser.add_argument('--source', choices=['google', 'pinterest'], default='pinterest', help='Source to scrape (default: pinterest)')
    args = parser.parse_args()

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    driver = setup_driver(headless=not args.visible)
    try:
        if args.source == 'pinterest':
            urls = fetch_image_urls_pinterest(args.query, args.limit, driver)
        else:
            urls = fetch_image_urls(args.query, args.limit, driver)
    finally:
        driver.quit()

    print(f"Found {len(urls)} image URLs, downloading...")
    downloaded = 0
    saved_paths = []
    for i, url in enumerate(urls, start=1):
        path = download_image(url, out_dir, i)
        if path:
            downloaded += 1
            saved_paths.append(path)
            print(f"{downloaded}. {path}")
        else:
            print(f"Failed to download: {url}")

    print(f"Done. {downloaded}/{len(urls)} images downloaded to {out_dir}")

    if downloaded:
        make_gallery(out_dir, saved_paths)


if __name__ == '__main__':
    main()
