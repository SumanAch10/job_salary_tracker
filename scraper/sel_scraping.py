# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# # /usr/bin/brave-browser
# # scraper/config.py

# SEARCH_CONFIG = {
#     "jobs": [
#         "data analyst",
#         "data scientist", 
#         "machine learning engineer",
#         "software engineer",
#         "business intelligence analyst",
#         "data engineer",
#         "AI engineer",
#         "backend engineer",
#         "frontend engineer",
#         "full stack engineer",
#     ],
#     "locations": [
#         "New York",
#         "San Francisco",
#         "Austin",
#         "Seattle",
#         "Chicago",
#         "Remote",
#     ],
#     "max_pages": 2,      # pages per search (15 jobs per page)
#     "delay_min": 3,      # minimum seconds between requests
#     "delay_max": 7,      # maximum seconds between requests
# }

# SELECTORS = {
#     "title":    '[data-testid="jobsearch-JobInfoHeader-title"]',
#     "company":  '[data-testid="inlineHeader-companyName"]',
#     "location": '[data-testid="inlineHeader-companyLocation"]',  
#     "salary":   '[data-testid="jobsearch-OtherJobDetailsContainer"]',   
#     "job_type": '[aria-label="Job type"]',
# }

# options = Options()

# # Run browser invisibly — no window appears
# options.add_argument("--headless")

# # Required on Linux — Chrome/Brave was designed for desktop
# options.add_argument("--no-sandbox")

# # Linux uses /dev/shm for shared memory — it's often too small
# # This tells browser to use /tmp instead — prevents crashe
# options.add_argument("--disable-dev-shm-usage")
# options.binary_location = "/usr/bin/brave-browser"

# service = Service(ChromeDriverManager().install())

# driver = webdriver.Chrome(                       # launch browser
#     service=service,                             # using this driver
#     options=options                              # with these preferences
# )

# driver.get("https://www.indeed.com/jobs?q=data+analyst&l=New+York")

# driver.quit()


import time
import random
import sys
import os

# Add project root to path so we can import from db/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from db.database import get_session, RawPosting
from scraper.config import SEARCH_CONFIG

# ─────────────────────────────────────────
# All selectors in one place
# If Indeed changes their HTML, update here only
# ─────────────────────────────────────────
SELECTORS = {
    "title":    '[data-testid="jobsearch-JobInfoHeader-title"]',
    "company":  '[data-testid="inlineHeader-companyName"]',
    "location": '[data-testid="inlineHeader-companyLocation"]',
    "salary":   '[data-testid="jobsearch-OtherJobDetailsContainer"]',
    "job_type": '[aria-label="Job type"]',
}


def create_driver():
    """
    Creates and returns a configured Brave browser driver.
    Called once at the start — reused for all scraping.
    """
    options = Options()
    options.add_argument("--headless")           # invisible — remove to watch it
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    options.binary_location = "/usr/bin/brave-browser"

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def extract_text(driver, selector, timeout=5):
    """
    Tries to find an element and return its text.
    Returns None if element not found — many fields are missing on real postings.
    
    Why timeout=5: we don't wait long for optional fields like salary.
    For required fields like title we'd use a longer timeout.
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        return element.text.strip()
    except:
        return None  # field simply doesn't exist on this posting


def get_job_urls_from_search(driver, search_url):
    """
    Opens a search results page and collects all job URLs.
    Returns a list of (url, indeed_job_id) tuples.
    
    Why collect URLs first instead of scraping directly?
    Search results page only shows preview cards.
    Full data (salary, job type) is only on individual job pages.
    """
    driver.get(search_url)
    
    # Wait for job cards to appear
    # Why: Indeed loads cards via JavaScript — they're not in initial HTML
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="slider_item"]'))
        )
    except:
        print(f"No job cards found for: {search_url}")
        return []
    
    # Small extra wait for all cards to finish loading
    time.sleep(2)
    
    # Find all job card links
    job_links = driver.find_elements(By.CSS_SELECTOR, 'a[data-jk]')
    
    urls = []
    for link in job_links:
        href = link.get_attribute('href')
        job_id = link.get_attribute('data-jk')  # Indeed's unique job ID
        if href and job_id:
            urls.append((href, job_id))
    
    print(f"Found {len(urls)} jobs on page")
    return urls


def scrape_job_page(driver, url, indeed_job_id):
    """
    Opens one job page and extracts all fields.
    Returns a dict of raw scraped data.
    
    Why return a dict instead of directly creating a DB object?
    Keeps scraping logic separate from database logic.
    Easier to debug — print the dict to see exactly what was scraped.
    """
    driver.get(url)
    
    # Wait for title to appear — confirms page loaded
    # Title is our required field — if it's missing, page didn't load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["title"]))
        )
    except:
        print(f"Page failed to load: {url}")
        return None
    
    # Extra wait for dynamic content
    time.sleep(1)
    
    # Extract each field — None is fine for optional fields
    title    = extract_text(driver, SELECTORS["title"])
    company  = extract_text(driver, SELECTORS["company"])
    location = extract_text(driver, SELECTORS["location"])
    salary   = extract_text(driver, SELECTORS["salary"])
    job_type = extract_text(driver, SELECTORS["job_type"])
    
    # Skip this job if we couldn't get title or company
    # These are required — a row without them is useless
    if not title or not company:
        print(f"Skipping — missing title or company: {url}")
        return None
    
    return {
        "title":         title,
        "company":       company,
        "location":      location,
        "salary_raw":    salary,
        "job_type":      job_type,
        "url":           url,
        "indeed_job_id": indeed_job_id,
    }


def save_to_db(job_data):
    """
    Saves one job dict to raw_postings table.
    
    Why check for duplicates?
    Same job appears in multiple searches (e.g. "data analyst New York" 
    and "data analyst Remote" might return same posting).
    indeed_job_id is UNIQUE in our schema — duplicate insert would crash.
    So we check first, skip if already exists.
    """
    with get_session() as session:
        # Check if this job already exists
        existing = session.query(RawPosting).filter_by(
            indeed_job_id=job_data["indeed_job_id"]
        ).first()
        
        if existing:
            print(f"Already exists, skipping: {job_data['title']}")
            return False
        
        # Create new row
        raw_posting = RawPosting(
            title         = job_data["title"],
            company       = job_data["company"],
            location      = job_data["location"],
            salary_raw    = job_data["salary_raw"],
            job_type      = job_data["job_type"],
            url           = job_data["url"],
            indeed_job_id = job_data["indeed_job_id"],
        )
        
        session.add(raw_posting)
        print(f"Saved: {job_data['title']} at {job_data['company']}")
        return True


def build_search_url(job_title, location, page=0):
    """
    Builds Indeed search URL from components.
    page=0 is first page, page=1 is second page (Indeed uses start=10, start=20)
    """
    query = job_title.replace(" ", "+")
    loc   = location.replace(" ", "+")
    start = page * 10
    return f"https://www.indeed.com/jobs?q={query}&l={loc}&start={start}"


def run_scraper():
    """
    Main function — runs the full scraping pipeline.
    Loops through all search queries and pages defined in config.
    """
    driver = create_driver()
    
    total_saved = 0
    total_seen  = 0
    
    try:
        for job_title in SEARCH_CONFIG["jobs"]:
            for location in SEARCH_CONFIG["locations"]:
                for page in range(SEARCH_CONFIG["max_pages"]):
                    
                    search_url = build_search_url(job_title, location, page)
                    print(f"\nScraping: {job_title} in {location} (page {page + 1})")
                    print(f"URL: {search_url}")
                    
                    # Get all job URLs from this search page
                    job_urls = get_job_urls_from_search(driver, search_url)
                    
                    # Visit each job page and extract data
                    for url, job_id in job_urls:
                        total_seen += 1
                        
                        # Scrape the job page
                        job_data = scrape_job_page(driver, url, job_id)
                        
                        if job_data:
                            # Immediately save to DB
                            saved = save_to_db(job_data)
                            if saved:
                                total_saved += 1
                        
                        # Random delay — looks human, avoids getting blocked
                        delay = random.uniform(
                            SEARCH_CONFIG["delay_min"],
                            SEARCH_CONFIG["delay_max"]
                        )
                        print(f"Waiting {delay:.1f}s...")
                        time.sleep(delay)
                    
                    # Longer delay between search pages
                    time.sleep(random.uniform(5, 10))
    
    except KeyboardInterrupt:
        # Ctrl+C gracefully stops the scraper
        # Data already saved to DB — nothing lost
        print("\nScraper stopped by user")
    
    finally:
        driver.quit()
        print(f"\nDone. Seen: {total_seen}, Saved: {total_saved}")


if __name__ == "__main__":
    run_scraper()