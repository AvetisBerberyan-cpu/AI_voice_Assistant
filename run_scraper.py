import subprocess
import sys
from data_scraper import scrape_bank, BANKS
from pathlib import Path


# Generate banks_data.py with full data string
def generate_banks_data():
    all_data_parts = []
    for bank_key in BANKS:
        full_bank = scrape_bank(bank_key)
        all_data_parts.append(full_bank)

    full_data = "\n\n***\n\n".join(all_data_parts)

    banks_data_content = f"""# Generated bank data - full concatenated string for LLM context

FULL_BANK_DATA = '''{full_data}'''
"""

    Path("banks_data.py").write_text(banks_data_content, encoding="utf-8")
    print("Generated banks_data.py with full data.")


if __name__ == "__main__":
    generate_banks_data()
