from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError
from bs4 import BeautifulSoup
from itertools import cycle
import threading
import time
import sys
import pandas as pd
import getpass

email_input = input("Enter your email: ")
password_input = getpass.getpass("Enter your password: ")

loading_indicators = cycle(["|", "/", "-", "\\"])


def loading_message():
    while scraping_in_progress:
        sys.stdout.write(f"\rScraping... {next(loading_indicators)}")
        sys.stdout.flush()
        time.sleep(0.2)


def scrape_current_page(page):
    html = page.inner_html("div.row.panel-print")
    soup = BeautifulSoup(html, "html.parser")
    jobs = soup.find_all("a", attrs={"id": "job_position_title"})
    companies = [
        span
        for span in soup.find_all("span", class_="text")
        if "text-status" not in span.get("class")
        and "text-job-status" not in span.get("class")
        and "text-compare" not in span.get("class")
    ]
    job_company_list = [
        (job.text, company.text) for job, company in zip(jobs, companies)
    ]
    return job_company_list


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(
        "https://myjobstreet.jobstreet.com.sg/home/login.php?site=sg&language_code=3"
    )
    email_locator = page.locator("#login_id")
    password_locator = page.locator("#password")
    login_locator = page.locator("#btn_login")
    application_locator = page.locator(
        'a[data-automation="profile-bar-job-application-btn"]'
    )
    email_locator.fill(email_input)
    password_locator.fill(password_input)
    login_locator.click()
    application_locator.click()

    all_data = []

    found_next_button = True
    while found_next_button:
        scraping_in_progress = True
        loading_thread = threading.Thread(target=loading_message)
        loading_thread.daemon = True
        loading_thread.start()

        current_page_data = scrape_current_page(page)
        # for job, company in current_page_data:
        #     print("Job Title:", job.text)
        #     print("Company:", company.text)
        #     print("\n")  # Add a newline for readability

        all_data.extend(current_page_data)

        try:
            next_locator = page.wait_for_selector("#pagination_next", timeout=5000)
            next_locator.click()
        except TimeoutError:
            found_next_button = False
            break

        scraping_in_progress = False
        loading_thread.join()

        page.wait_for_load_state("networkidle")

df = pd.DataFrame(all_data, columns=["Job Title", "Company"])
df.to_excel("testing.xlsx", sheet_name="Sheet1")
print("\nScraping completed! Data saved successfully.")
