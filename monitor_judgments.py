import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from curl_cffi import requests

LHC_URL = "https://data.lhc.gov.pk/reported_judgments/judgments_approved_for_reporting"
SC_URL = "https://www.supremecourt.gov.pk/latest-judgements/"

LHC_FILE = "lhc_judgments.md"
SC_FILE = "sc_judgments.md"

def fetch_content(url):
    try:
        # Use curl_cffi to impersonate Chrome and bypass bot protection / TLS fingerprinting
        response = requests.get(url, impersonate="chrome110", timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_lhc(html):
    soup = BeautifulSoup(html, 'html.parser')
    judgments = []
    # LHC structure: Based on browser subagent, it's a list or table under 'Latest Reported Judgments'
    # Finding elements with case info
    for card in soup.select('.views-row'):
        try:
            case_info = card.get_text(strip=True, separator=' ')
            # Example: Immigration 77067/25 (Muhammad Usman Dar Vs Federation of Pakistan etc) by Mr. Justice Muhammad Sajid Mehmood Sethi (Uploaded: 26-02-2026)
            link_tag = card.find('a', href=True)
            link = "https://data.lhc.gov.pk" + link_tag['href'] if link_tag else "No link"
            judgments.append({
                "description": case_info,
                "link": link
            })
        except Exception:
            continue
    return judgments

def parse_sc(html):
    soup = BeautifulSoup(html, 'html.parser')
    judgments = []
    table = soup.find('table')
    if not table:
        return []
    
    rows = table.find_all('tr')[1:] # Skip header
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 5:
            try:
                judgments.append({
                    "sr": cols[0].text.strip(),
                    "subject": cols[1].text.strip(),
                    "case_no": cols[2].text.strip(),
                    "title": cols[3].text.strip(),
                    "judge": cols[4].text.strip(),
                    "uploaded": cols[5].text.strip() if len(cols) > 5 else "N/A",
                    "link": cols[2].find('a')['href'] if cols[2].find('a') else "No link"
                })
            except Exception:
                continue
    return judgments

def update_markdown(filename, new_judgments, title, header_cols):
    if not new_judgments:
        return

    existing_content = ""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            existing_content = f.read()

    # Create table if file doesn't exist
    if not existing_content:
        table_header = f"# {title}\n\nLast Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        table_header += "| " + " | ".join(header_cols) + " |\n"
        table_header += "| " + " | ".join(["---"] * len(header_cols)) + " |\n"
        existing_content = table_header

    lines = existing_content.split('\n')
    
    # Filter out only the new ones that aren't already in the file
    # We use Case No/Description as unique identifiers
    to_add = []
    for j in new_judgments:
        # Check if already in file
        if j.get('case_no') and j['case_no'] in existing_content:
            continue
        if j.get('description') and j['description'][:50] in existing_content: # heuristic for LHC
            continue
        
        # Format as row
        if "description" in j: # LHC
            row = f"| {j['description']} | [Link]({j['link']}) |"
        else: # SC
            row = f"| {j['sr']} | {j['subject']} | {j['case_no']} | {j['title']} | {j['judge']} | {j['uploaded']} | [Link]({j['link']}) |"
        to_add.append(row)

    if to_add:
        # Insert after header (top of table)
        # Find where the table starts (after the separator line)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('| --- |'):
                insert_idx = i + 1
                break
        
        if insert_idx == 0: # Header not found, append to end
            lines.extend(to_add)
        else:
            for i, row in enumerate(to_add):
                lines.insert(insert_idx + i, row)
        
        # Update timestamp
        for i, line in enumerate(lines):
            if line.startswith("Last Updated:"):
                lines[i] = f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                break

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"Updated {filename} with {len(to_add)} new entries.")
    else:
        print(f"No new entries for {filename}.")

def main():
    print("Fetching LHC judgments...")
    lhc_html = fetch_content(LHC_URL)
    if lhc_html:
        lhc_judgments = parse_lhc(lhc_html)
        update_markdown(LHC_FILE, lhc_judgments, "LHC Reported Judgments", ["Description", "Link"])

    print("\nFetching Supreme Court judgments...")
    sc_html = fetch_content(SC_URL)
    if sc_html:
        sc_judgments = parse_sc(sc_html)
        update_markdown(SC_FILE, sc_judgments, "Supreme Court Latest Judgments", ["Sr", "Subject", "Case No", "Title", "Judge", "Uploaded", "Link"])

if __name__ == "__main__":
    main()
