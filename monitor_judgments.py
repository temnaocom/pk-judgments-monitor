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
        print(f"Fetched {len(response.text)} bytes from {url}")
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_lhc(html):
    soup = BeautifulSoup(html, 'html.parser')
    judgments = []
    
    for link_tag in soup.find_all('a', href=True):
        if 'appjudgments' in link_tag['href'].lower():
            try:
                td = link_tag.find_parent('td')
                if not td:
                    continue
                case_info = td.get_text(separator=' ', strip=True)
                # Clean up multiple spaces
                case_info = re.sub(r'\s+', ' ', case_info)
                
                link = link_tag['href']
                if not link.startswith('http'):
                    link = "https://data.lhc.gov.pk" + link
                
                judgments.append({
                    "description": case_info,
                    "link": link
                })
            except Exception:
                continue
    print(f"Parsed {len(judgments)} LHC judgments.")
    if not judgments:
        print(f"LHC parsing found 0. HTML snippet: {html[:1000]}")
    return judgments

def parse_sc(html):
    soup = BeautifulSoup(html, 'html.parser')
    judgments = []
    
    # Look for any rows containing a PDF link (usually how judgments are linked)
    pdf_links = [a for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
    
    for link_tag in pdf_links:
        tr = link_tag.find_parent('tr')
        if tr:
            cols = tr.find_all(['td', 'th'])
            if len(cols) >= 4:
                try:
                    text_parts = [c.get_text(separator=' ', strip=True) for c in cols]
                    judgments.append({
                        "sr": text_parts[0] if len(text_parts)>0 else "",
                        "subject": text_parts[1] if len(text_parts)>1 else "",
                        "case_no": text_parts[2] if len(text_parts)>2 else "",
                        "title": text_parts[3] if len(text_parts)>3 else "",
                        "judge": text_parts[4] if len(text_parts)>4 else "",
                        "uploaded": text_parts[5] if len(text_parts)>5 else "N/A",
                        "link": link_tag['href']
                    })
                except Exception:
                    continue

    print(f"Parsed {len(judgments)} SC judgments.")
    if not judgments:
        print(f"SC parsing found 0. HTML snippet: {html[:1000]}")
    return judgments

def update_markdown(filename, new_judgments, title, header_cols):
    if not new_judgments:
        print(f"No judgments passed to update_markdown for {filename}")
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
    
    to_add = []
    for j in new_judgments:
        # Check if already in file
        if j.get('case_no') and j['case_no'] in existing_content:
            continue
        if j.get('description') and j['description'][:50] in existing_content: 
            continue
        
        # Format as row
        if "description" in j: # LHC
            row = f"| {j['description']} | [Link]({j['link']}) |"
        else: # SC
            row = f"| {j['sr']} | {j['subject']} | {j['case_no']} | {j['title']} | {j['judge']} | {j['uploaded']} | [Link]({j['link']}) |"
        to_add.append(row)

    if to_add:
        # Insert after header
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('| --- |'):
                insert_idx = i + 1
                break
        
        if insert_idx == 0: 
            lines.extend(to_add)
        else:
            for i, row in enumerate(to_add):
                lines.insert(insert_idx + i, row)
        
        # Count and update time
        for i, line in enumerate(lines):
            if line.startswith("Last Updated:"):
                lines[i] = f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                break

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"Updated {filename} with {len(to_add)} new entries.")
    else:
        print(f"No new entries for {filename} after deduplication.")

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
