from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure options
options = Options()
options.add_argument("--no-sandbox")        # required on Linux
options.add_argument("--disable-dev-shm-usage")  # prevents crashes on Linux

# Tell Selenium to use Brave instead of Chrome
options.binary_location = "/usr/bin/brave-browser"

# webdriver-manager downloads the correct ChromeDriver automatically
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

# Test it
driver.get("https://www.indeed.com/jobs?q=data+analyst&l=New+York")

print("Page title:", driver.title)
print("HTML length:", len(driver.page_source))

driver.quit()
print("Selenium is working with Brave!")