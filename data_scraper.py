import requests
from bs4 import BeautifulSoup
import os
import re

# Armenian banks URLs - key pages for credits/loans, deposits, branches
BANKS = {
    "mellat": {
        "name": "Mellat Bank",
        "base": "https://mellatbank.am",
        "credits": [
            "https://mellatbank.am/hy/loans/",
            "https://mellatbank.am/hy/credits/",
        ],
        "deposits": ["https://mellatbank.am/hy/deposits/"],
        "branches": ["https://mellatbank.am/hy/contacts/branches/"],
    },
    "ameria": {
        "name": "Ameriabank",
        "base": "https://ameriabank.am",
        "credits": [
            "https://ameriabank.am/en/private/loans.html",
            "https://ameriabank.am/hy/private/loans.html",
        ],
        "deposits": [
            "https://ameriabank.am/en/private/deposits.html",
            "https://ameriabank.am/hy/private/deposits.html",
        ],
        "branches": [
            "https://ameriabank.am/en/contacts/branches.html",
            "https://ameriabank.am/hy/contacts/branches.html",
        ],
    },
    "ardshin": {
        "name": "Ardshinbank",
        "base": "https://ardshinbank.am",
        "credits": [
            "https://ardshinbank.am/en/individuals/loans/",
            "https://ardshinbank.am/hy/individuals/loans/",
        ],
        "deposits": [
            "https://ardshinbank.am/en/individuals/deposits/",
            "https://ardshinbank.am/hy/individuals/deposits/",
        ],
        "branches": [
            "https://ardshinbank.am/en/contacts/branches/",
            "https://ardshinbank.am/hy/contacts/branches/",
        ],
    },
    "converse": {
        "name": "Converse Bank",
        "base": "https://www.conversebank.am",
        "credits": [
            "https://www.conversebank.am/en/loans/",
            "https://www.conversebank.am/am/loans/",
        ],
        "deposits": [
            "https://www.conversebank.am/en/deposits/",
            "https://www.conversebank.am/am/deposits/",
        ],
        "branches": [
            "https://www.conversebank.am/en/contacts/branches/",
            "https://www.conversebank.am/am/contacts/branches/",
        ],
    },
}

DATA_DIR = "data"


def clean_text(text):
    # Clean HTML, extra whitespace, non-important
    text = re.sub(r"\s+", " ", text)
    text = re.sub(
        r"[^\u0530-\u058F\u0041-\u007A\u0030-\u0039\s\.,:;\-\(\)\%\&€$]+", "", text
    )  # ARM/EN/nums/punct
    return text.strip()


def scrape_section(urls, section):
    content = ""
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "lxml")
            # Remove scripts/styles
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.decompose()
            text = soup.get_text()
            content += f"\n--- {url} ---\n{clean_text(text)}\n"
        except Exception as e:
            content += f"\nError scraping {url}: {e}\n"
    return content


def scrape_bank(bank_key):
    bank = BANKS[bank_key]
    os.makedirs(DATA_DIR, exist_ok=True)

    sections = {}
    for section in ["credits", "deposits", "branches"]:
        urls = bank[section]
        content = scrape_section(urls, section)
        filename = f"{DATA_DIR}/{bank_key}_{section}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        sections[section] = content
        print(f"Saved {filename}")

    # Full bank concat
    full = f"{bank['name']}:\nCredits: {sections['credits']}\nDeposits: {sections['deposits']}\nBranches: {sections['branches']}"
    full_filename = f"{DATA_DIR}/{bank_key}_full.txt"
    with open(full_filename, "w", encoding="utf-8") as f:
        f.write(full)
    print(f"Saved full {full_filename}")
    return full


if __name__ == "__main__":
    all_data = ""
    for bank_key in BANKS:
        full_bank = scrape_bank(bank_key)
        all_data += full_bank + "\n\n"
    print("Scraping complete")
