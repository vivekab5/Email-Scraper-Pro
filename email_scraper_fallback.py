import requests
from bs4 import BeautifulSoup
import re
import csv
from html import unescape
from urllib.parse import urljoin
import time
import random
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {'User-Agent': 'Mozilla/5.0'}
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
FALLBACK_PATHS = ["/contact", "/privacy", "/privacy-policy", "/contact-us", "/pages/contact-us", "/pages/privacy-policy"]

# Add your proxy list here (format: http://user:pass@ip:port or just http://ip:port)
PROXIES = [
    # "http://123.123.123.123:8000",
    # "http://username:password@123.123.123.124:8000",
]

def get_random_proxy():
    if PROXIES:
        return {"http": random.choice(PROXIES), "https": random.choice(PROXIES)}
    return None

def extract_emails_from_soup(soup):
    combined_text = soup.get_text() + soup.prettify()
    decoded_text = unescape(combined_text)

    normal_emails = re.findall(EMAIL_REGEX, decoded_text)

    obfuscated = re.findall(
        r"[a-zA-Z0-9_.+-]+\s?\[at\]\s?[a-zA-Z0-9-]+\s?\[dot\]\s?[a-zA-Z0-9-.]+", decoded_text
    )
    obfuscated_fixed = [
        email.replace("[at]", "@").replace("[dot]", ".").replace(" ", "") for email in obfuscated
    ]

    return list(set(normal_emails + obfuscated_fixed))

# get web

def scrape_emails_from_url(url):
    session = requests.Session()
    proxy = get_random_proxy()
    try:
        time.sleep(random.uniform(1, 3))  
        res = session.get(url, headers=HEADERS, proxies=proxy, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        emails = extract_emails_from_soup(soup)

        if emails:
            return (url, emails)

        for path in FALLBACK_PATHS:
            fallback_url = urljoin(url, path)
            time.sleep(random.uniform(1, 2))
            res = session.get(fallback_url, headers=HEADERS, proxies=proxy, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            emails = extract_emails_from_soup(soup)
            if emails:
                return (url, emails)

        
        os.makedirs("failed_pages", exist_ok=True)
        with open(f"failed_pages/{url.replace('https://', '').replace('http://', '').replace('/', '_')}.html", "w", encoding="utf-8") as f:
            f.write(res.text)

    except Exception as e:
        print(f"❌ Error with {url}: {e}")
    return (url, [])

def main():
    input_file = "websites.txt"
    output_file = "emails_found.csv"
    max_threads = 5

    with open(input_file, "r") as f:
        websites = [line.strip() for line in f if line.strip()]

    results = []

    print(f"🚀 Scraping {len(websites)} websites with {max_threads} threads...\n")

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_url = {executor.submit(scrape_emails_from_url, url): url for url in websites}

        for idx, future in enumerate(as_completed(future_to_url), 1):
            url, emails = future.result()
            print(f"[{idx}/{len(websites)}] {url} — {'✅ Found' if emails else '❌ No emails'}")
            results.append((url, ", ".join(emails) if emails else "No emails found"))

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Website", "Emails Found"])
        writer.writerows(results)

    print("\n🎉 Scraping complete! Results saved to:", output_file)

if __name__ == "__main__":
    main()
