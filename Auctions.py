import json
import time
import random
import os
import requests
import shutil
import urllib.parse
import subprocess
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image

# ==============================================================================
# --- GLOBAL CONFIGURATION ---
# ==============================================================================

# --- AI Configuration for Analysis ---
MODEL_FALLBACK_LIST = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite"
]
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 15
DELAY_BETWEEN_BATCHES = 5
BATCH_SIZE = 2

# --- Scraper Configuration ---
MIN_WAIT = 5
MAX_WAIT = 10

# --- Site-Specific Configurations ---
SITE_CONFIGS = {
    "transitional": {
        "name": "Transitional Design",
        "domain": "auctions.transitionaldesign.net",
        "SCRAPED_DATA_FILE": "transitional_listings.json",
        "PICS_FOLDER": "transitional_pics",
        "ANALYZED_DEALS_FILE": "transitional_deals.json",
        "SORTED_FILE_PREFIX": "trans"
    },
    "greatfinds": {
        "name": "Great Finds Auction",
        "domain": "greatfindsauction.com",
        "SCRAPED_DATA_FILE": "greatfinds_listings.json",
        "PICS_FOLDER": "greatfinds_pics",
        "ANALYZED_DEALS_FILE": "greatfinds_deals.json",
        "SORTED_FILE_PREFIX": "greatfinds"
    }
}

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auction Item Analysis</title>
    <style>
        :root {
            --bg-color: #1a1a1a; --table-bg-color: #2c2c2c; --header-bg-color: #3a3a3a;
            --header-hover-bg-color: #4a4a4a; --row-even-bg-color: #333333; --row-odd-bg-color: #2c2c2c;
            --border-color: #444444; --text-color: #e0e0e0; --link-color: #4a90e2;
            --link-hover-color: #81b5f5; --sort-indicator-color: #81b5f5;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; padding: 2rem; line-height: 1.6; }
        h1 { text-align: center; color: #ffffff; font-weight: 300; margin-bottom: 2rem; }
        .table-container { max-width: 1200px; margin: auto; overflow-x: auto; border-radius: 8px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); }
        table { width: 100%; border-collapse: collapse; background-color: var(--table-bg-color); border-spacing: 0; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid var(--border-color); }
        thead th { background-color: var(--header-bg-color); color: #ffffff; font-weight: 600; position: sticky; top: 0; z-index: 10; }
        thead th[data-column] { cursor: pointer; transition: background-color 0.2s ease-in-out; user-select: none; }
        thead th[data-column]:hover { background-color: var(--header-hover-bg-color); }
        tbody tr:nth-child(even) { background-color: var(--row-even-bg-color); }
        tbody tr:nth-child(odd) { background-color: var(--row-odd-bg-color); }
        tbody tr:hover { background-color: var(--header-hover-bg-color); }
        td { font-size: 0.95em; }
        td:nth-child(3) { font-family: 'Courier New', Courier, monospace; text-align: right; white-space: nowrap; }
        td:nth-child(4) { text-align: center; }
        a { color: var(--link-color); text-decoration: none; transition: color 0.2s ease-in-out; }
        a:hover { color: var(--link-hover-color); text-decoration: underline; }
        .sort-indicator { color: var(--sort-indicator-color); font-size: 0.8em; margin-left: 8px; display: inline-block; width: 10px; }
    </style>
</head>
<body>
    <h1>Auction Item Analysis</h1>
    <div class="table-container"><table><thead><tr><th data-column="name">Item Name <span class="sort-indicator"></span></th><th data-column="category">Category <span class="sort-indicator"></span></th><th data-column="price">Market Value <span class="sort-indicator"></span></th><th>Google Search</th></tr></thead><tbody id="data-table-body"></tbody></table></div>
    
    <script type="application/json" id="auctionData">
        __JSON_DATA_PLACEHOLDER__
    </script>

    <script>
        const jsonData = JSON.parse(document.getElementById('auctionData').textContent);
        const tableBody = document.getElementById('data-table-body');
        const headers = document.querySelectorAll('thead th[data-column]');
        let currentSort = { column: 'price', isAscending: false };
        function getItemName(item) { if (typeof item.item_identification === 'object' && item.item_identification !== null) { return item.item_identification.item_name || 'N/A'; } return item.item_identification; }
        function getCategory(itemName) { const name = itemName.toLowerCase(); if (name.includes('furniture') || name.includes('table') || name.includes('desk') || name.includes('cabinet') || name.includes('dresser')) return 'Furniture'; if (name.includes('painting') || name.includes('print') || name.includes('art')) return 'Art/Prints'; if (name.includes('dinnerware') || name.includes('china') || name.includes('porcelain')) return 'Pottery/China'; if (name.includes('mirror') || name.includes('lamp')) return 'Decor/Lighting'; if (name.includes('glassware') || name.includes('crystal')) return 'Glassware'; if (name.includes('blower') || name.includes('tool')) return 'Tools/Equipment'; if (name.includes('toy')) return 'Toys/Games'; if (name.includes('cards')) return 'Collectibles'; return 'Miscellaneous'; }
        function populateTable() { tableBody.innerHTML = ''; jsonData.forEach(item => { const row = document.createElement('tr'); const itemName = getItemName(item); const nameCell = document.createElement('td'); const nameLink = document.createElement('a'); nameLink.href = item.original_listing.url; nameLink.textContent = itemName; nameLink.target = "_blank"; nameCell.appendChild(nameLink); const categoryCell = document.createElement('td'); categoryCell.textContent = getCategory(itemName); const priceCell = document.createElement('td'); priceCell.textContent = (item.estimated_market_value || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }); const linkCell = document.createElement('td'); const searchLink = document.createElement('a'); searchLink.href = `https://www.google.com/search?q=${encodeURIComponent(itemName)}`; searchLink.textContent = 'Search'; searchLink.target = "_blank"; linkCell.appendChild(searchLink); row.appendChild(nameCell); row.appendChild(categoryCell); row.appendChild(priceCell); row.appendChild(linkCell); tableBody.appendChild(row); }); }
        function sortData(column) { const isNumeric = column === 'price'; if (currentSort.column === column) { currentSort.isAscending = !currentSort.isAscending; } else { currentSort.column = column; currentSort.isAscending = !isNumeric; } jsonData.sort((a, b) => { let valA, valB; if (isNumeric) { valA = a.estimated_market_value || 0; valB = b.estimated_market_value || 0; } else { const nameA = getItemName(a); const nameB = getItemName(b); if (column === 'name') { valA = nameA.toLowerCase(); valB = nameB.toLowerCase(); } else if (column === 'category') { valA = getCategory(nameA); valB = getCategory(nameB); } } let comparison = 0; if (valA > valB) { comparison = 1; } else if (valA < valB) { comparison = -1; } return currentSort.isAscending ? comparison : comparison * -1; }); updateSortIndicators(); populateTable(); }
        function updateSortIndicators() { headers.forEach(header => { const indicator = header.querySelector('.sort-indicator'); if (header.dataset.column === currentSort.column) { indicator.textContent = currentSort.isAscending ? ' ▲' : ' ▼'; } else { indicator.textContent = ''; } }); }
        headers.forEach(header => { header.addEventListener('click', () => { sortData(header.dataset.column); }); });
        sortData('price');
    </script>
</body>
</html>
"""

# --- Custom Exceptions ---
class ModelFallbackException(Exception):
    pass

# ==============================================================================
# --- HELPER & CORE FUNCTIONS ---
# ==============================================================================

def load_json_data(filename):
    if not os.path.exists(filename): return []
    try:
        with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
    except (json.JSONDecodeError, IOError): return []

def download_image(url, filepath):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko/20100101)'}
        response = requests.get(url, headers=headers, stream=True, timeout=20)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024): f.write(chunk)
            return True
        return False
    except requests.exceptions.RequestException: return False

def chunk_list(data, size):
    for i in range(0, len(data), size): yield data[i:i + size]

def configure_ai_client():
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("API key not found in .env file.")
    client = genai.Client()
    print("Google AI Client initialized successfully.")
    return client

# ==============================================================================
# --- PART 1: SCRAPER ---
# ==============================================================================

def setup_driver():
    service = webdriver.chrome.service.Service()
    options = webdriver.ChromeOptions()
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko/20100101)')
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=service, options=options)

def get_all_item_links(driver):
    item_links = []
    page_count = 1
    while True:
        print(f"Scanning page {page_count}...")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.galleryUnit h2.galleryTitle a, h2.title.inlinebidding a")))
        links_on_page = driver.find_elements(By.CSS_SELECTOR, "div.galleryUnit h2.galleryTitle a, h2.title.inlinebidding a")
        first_item_on_page = links_on_page[0]
        for link in links_on_page:
            url = link.get_attribute('href')
            if url and url not in [p['url'] for p in item_links]: item_links.append({'id': url, 'url': url})
        try:
            next_page_link = driver.find_element(By.LINK_TEXT, "»")
            if "disabled" in next_page_link.find_element(By.XPATH, "./..").get_attribute("class"): break
            driver.execute_script("arguments[0].scrollIntoView(true);", next_page_link)
            time.sleep(1); next_page_link.click(); page_count += 1
            WebDriverWait(driver, 20).until(EC.staleness_of(first_item_on_page))
            time.sleep(2)
        except NoSuchElementException: break
    return item_links

def scrape_transitional(driver, post, config):
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.panel-body.description")))
    time.sleep(3)
    title = driver.find_element(By.CSS_SELECTOR, 'h3.detail__title').text.strip()
    price = driver.execute_script("return document.querySelector('span.detail__price--current span.NumberPart')?.innerText || 'N/A';").strip()
    image_filenames = []
    for idx, img_tag in enumerate(driver.find_elements(By.CSS_SELECTOR, "ul.es-slides img.img-thumbnail")):
        img_url = img_tag.get_attribute('data-full-size-src')
        if not img_url: continue
        unique_id = post['url'].strip('/').split('/')[-2]
        filepath = os.path.join(config['PICS_FOLDER'], f"{unique_id}_{idx + 1}.jpg")
        if download_image(img_url, filepath): image_filenames.append(f"{unique_id}_{idx + 1}.jpg")
    return {'post_id': post['id'], 'title': title, 'current_bid': f'${price}', 'url': post['url'], 'pics': image_filenames}

def scrape_greatfinds(driver, post, config):
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.detail__sectionBody.description")))
    time.sleep(3)
    title = driver.find_element(By.CSS_SELECTOR, 'h1.detail__title span').text.strip()
    price = driver.execute_script("return document.querySelector('span.detail__price--current span.NumberPart')?.innerText || 'N/A';").strip()
    image_filenames = []
    for idx, link_tag in enumerate(driver.find_elements(By.CSS_SELECTOR, "div.detail__imageThumbnails a")):
        img_url = link_tag.get_attribute('href')
        if not img_url: continue
        unique_id = post['url'].strip('/').split('/')[-2]
        filepath = os.path.join(config['PICS_FOLDER'], f"{unique_id}_{idx + 1}.jpg")
        if download_image(img_url, filepath): image_filenames.append(f"{unique_id}_{idx + 1}.jpg")
    return {'post_id': post['id'], 'title': title, 'current_bid': f'${price}', 'url': post['url'], 'pics': image_filenames}

def run_scraper(url, config, scraper_func):
    print(f"\n--- [STARTING STEP 1: SCRAPING {config['name']}] ---")
    os.makedirs(config['PICS_FOLDER'], exist_ok=True)
    driver = None
    try:
        driver = setup_driver()
        driver.get(url)
        all_links = get_all_item_links(driver)
        if not all_links:
            print("No items found on the auction page.")
            return False
        
        all_listings = []
        print(f"Found {len(all_links)} items. Starting to fetch details...")
        for i, post in enumerate(all_links):
            print(f"  ({i+1}/{len(all_links)}) Processing: {post['url']}")
            driver.get(post['url'])
            try:
                listing_data = scraper_func(driver, post, config)
                all_listings.append(listing_data)
                if i < len(all_links) - 1: time.sleep(random.uniform(MIN_WAIT, MAX_WAIT))
            except TimeoutException: print(f"  > Timed out. Skipping.")
        
        with open(config['SCRAPED_DATA_FILE'], 'w', encoding='utf-8') as f:
            json.dump(all_listings, f, indent=4)
        return True
    except Exception as e:
        print(f"A critical error occurred during scraping: {e}")
        return False
    finally:
        if driver: driver.quit()
        print(f"--- [COMPLETED STEP 1: SCRAPING] ---")

# ==============================================================================
# --- PART 2: AI ANALYSIS ---
# ==============================================================================

def analyze_deal_batch(client, batch, model_name, config):
    for attempt in range(MAX_RETRIES):
        try:
            prompt = f"""You are an expert reseller. Analyze {len(batch)} auction listings. For each, provide a JSON object with these exact keys: 'item_identification' (a simple, descriptive string), 'estimated_market_value' (a single number, no symbols), and 'original_listing' (the complete original listing object I provided). You MUST respond with a single, valid JSON array of {len(batch)} objects."""
            contents = [prompt]
            for post in batch:
                contents.append(f"\n--- NEW LISTING --- \n{json.dumps(post)}")
                for pic in post.get('pics', []):
                    try: contents.append(Image.open(os.path.join(config['PICS_FOLDER'], pic)))
                    except FileNotFoundError: pass
            response = client.models.generate_content(model=model_name, contents=contents, config=types.GenerateContentConfig(response_mime_type="application/json"))
            return json.loads(response.text)
        except Exception as e:
            if "429" in str(e).lower(): raise ModelFallbackException(str(e))
            elif "503" in str(e).lower(): time.sleep(RETRY_DELAY_SECONDS)
            else: raise ModelFallbackException(str(e))
    return None

def run_ai_analyzer(config, client):
    print("\n--- [STARTING STEP 2: AI PROFITABILITY ANALYSIS] ---")
    posts = load_json_data(config['SCRAPED_DATA_FILE'])
    if not posts: return True
    all_deals = []
    for i, batch in enumerate(chunk_list(posts, BATCH_SIZE)):
        print(f"\n--- Processing AI Batch {i+1} ---")
        model_idx = 0
        while model_idx < len(MODEL_FALLBACK_LIST):
            model = MODEL_FALLBACK_LIST[model_idx]
            try:
                ai_response = analyze_deal_batch(client, batch, model, config)
                if ai_response: all_deals.extend(ai_response); break
            except ModelFallbackException:
                model_idx += 1
                if model_idx >= len(MODEL_FALLBACK_LIST): print("All AI models failed for this batch.")
        if i < (len(posts) // BATCH_SIZE): time.sleep(DELAY_BETWEEN_BATCHES)
    with open(config['ANALYZED_DEALS_FILE'], 'w', encoding='utf-8') as f:
        json.dump(all_deals, f, indent=4)
    print(f"--- [COMPLETED STEP 2: AI ANALYSIS] ---")
    return True

# ==============================================================================
# --- PART 3 & 4: SORTING, HTML GENERATION, GITHUB PUSH ---
# ==============================================================================

def update_index_html(new_report_filename):
    """
    Adds a link to the new report at the top of index.html.
    Updated to parse the new filename format for link text.
    """
    print(f"\n--- Updating index.html ---")
    placeholder = "<!-- REPORT_LINKS_PLACEHOLDER -->"
    try:
        base_name = os.path.splitext(new_report_filename)[0]
        parts = base_name.split('_')
        prefix, date_part, time_part = parts[0], parts[2], parts[3].replace('-', ':')
        
        if prefix == 'design': site_name = 'Transitional Design'
        elif prefix == 'great': site_name = 'Great Finds'
        else: site_name = prefix.capitalize()
            
        link_text = f"{site_name} Report - {date_part} at {time_part}"
    except IndexError:
        link_text = new_report_filename

    new_link_html = f'            <li><a href="{new_report_filename}">{link_text}</a></li>'
    try:
        with open("index.html", 'r+', encoding='utf-8') as f:
            content = f.read()
            if new_link_html not in content:
                f.seek(0)
                f.write(content.replace(placeholder, f"{placeholder}\n{new_link_html}"))
                print(f"Successfully added link for '{new_report_filename}'.")
            else:
                print("Link for this report already exists in index.html.")
        return True
    except FileNotFoundError:
        print("Error: index.html not found. Cannot update archive page.")
        return False

def commit_and_push_to_github(filenames_to_add, commit_message):
    print("\n--- Pushing updates to GitHub ---")
    try:
        subprocess.run(["git", "add"] + filenames_to_add, check=True, capture_output=True)
        commit_result = subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True, text=True)
        if "nothing to commit" in commit_result.stdout or "no changes added to commit" in commit_result.stdout:
            print("No new changes to commit. GitHub is already up to date.")
            return True
        subprocess.run(["git", "push"], check=True, capture_output=True)
        load_dotenv()
        username, repo_name = os.getenv("GITHUB_USERNAME"), os.getenv("GITHUB_REPO_NAME")
        if username and repo_name:
            print(f"\nSuccess! View your updated archive at: https://{username}.github.io/{repo_name}/")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        error_output = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
        print(f"An error occurred during a Git operation: {error_output}")
        return False

def run_final_steps(config):
    """
    Sorts deals, creates the HTML report, updates the index, and pushes to GitHub.
    Uses the new 'design' and 'great' filename prefixes with full timestamps.
    """
    print("\n--- [STARTING FINAL STEPS: SORTING, REPORTING, UPLOADING] ---")
    try:
        data = load_json_data(config['ANALYZED_DEALS_FILE'])
        if not data:
            print("No analyzed deals found. Skipping final steps.")
            return False

        sorted_data = sorted(data, key=lambda item: item.get('estimated_market_value', 0), reverse=True)
        
        if config['SORTED_FILE_PREFIX'] == 'trans': site_prefix = 'design'
        elif config['SORTED_FILE_PREFIX'] == 'greatfinds': site_prefix = 'great'
        else: site_prefix = config['SORTED_FILE_PREFIX']
            
        datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        sorted_filename = f"{site_prefix}_{datetime_str}.json"
        html_filename = f"{site_prefix}_Report_{datetime_str}.html"
        
        with open(sorted_filename, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, indent=4)
        print(f"Sorted deals into '{sorted_filename}'")

        json_string_for_html = json.dumps(sorted_data, indent=4)
        final_html = HTML_TEMPLATE.replace("__JSON_DATA_PLACEHOLDER__", json_string_for_html)
        
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(final_html)
        print(f"Created HTML report: '{html_filename}'")

        if update_index_html(html_filename):
            return commit_and_push_to_github([html_filename, sorted_filename, "index.html"], f"Add report: {html_filename}")
        return False
    except Exception as e:
        print(f"An error occurred during final steps: {e}")
        return False

# ==============================================================================
# --- PART 5: CLEANUP ---
# ==============================================================================

def run_cleanup(config):
    print("\n--- [STARTING STEP 5: CLEANUP] ---")
    files_to_delete = [config['SCRAPED_DATA_FILE'], config['ANALYZED_DEALS_FILE']]
    for f in files_to_delete:
        if os.path.exists(f): os.remove(f); print(f"Deleted intermediate file: '{f}'")
    if os.path.exists(config['PICS_FOLDER']):
        shutil.rmtree(config['PICS_FOLDER']); print(f"Deleted pictures directory: '{config['PICS_FOLDER']}'")
    print("--- [COMPLETED STEP 5: CLEANUP] ---")

# ==============================================================================
# --- MAIN EXECUTION ORCHESTRATOR ---
# ==============================================================================

def main():
    url = ""
    while not url.startswith("http"):
        url = input("Please enter the full auction URL and press Enter: ")
    
    config, scraper_func = (None, None)
    if SITE_CONFIGS["transitional"]["domain"] in url:
        config, scraper_func = SITE_CONFIGS["transitional"], scrape_transitional
    elif SITE_CONFIGS["greatfinds"]["domain"] in url:
        config, scraper_func = SITE_CONFIGS["greatfinds"], scrape_greatfinds
    else:
        print("Error: URL does not match a known auction site."); return

    if not run_scraper(url, config, scraper_func):
        print("\nScraping step failed. Aborting."); return
        
    try:
        client = configure_ai_client()
        if not run_ai_analyzer(config, client):
            print("\nAI analysis step failed. Aborting."); return
        
        if run_final_steps(config):
            run_cleanup(config)
            print("\n\n>>> ALL STEPS COMPLETED SUCCESSFULLY! <<<")
        else:
            print("\nProcess finished, but final reporting or upload failed. Intermediate files were not deleted.")
    except Exception as e:
        print(f"\nA critical error occurred in the main process: {e}")

if __name__ == "__main__":
    main()