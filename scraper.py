 import os
import time
import json
import csv
import random
from datetime import datetime
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

# Пътят вътре в GitHub репото
MASTER_CSV = "master_jobs.csv"
PROGRESS_FILE = "last_id.txt"

def get_last_id():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return int(f.read().strip())
    return 13976 # Начална точка по подразбиране

def save_progress(current_id):
    with open(PROGRESS_FILE, 'w') as f:
        f.write(str(current_id))

def save_entry(row):
    file_exists = os.path.isfile(MASTER_CSV)
    with open(MASTER_CSV, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Date Posted', 'Position', 'City', 'Source Link', 'Parsing Timestamp', 'Company Name'])
        writer.writerows([row])

def run_the_gauntlet():
    print("--- INITIATING CLOUD-STALKER PROTOCOL ---")
    
    options = uc.ChromeOptions()
    options.add_argument("--headless") # GitHub Actions ВИНАГИ е headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = uc.Chrome(options=options)
    start_id = get_last_id()
    
    try:
        # Променяме лимита на малки порции, защото GitHub Actions има лимит от 6 часа на рън
        # Ще минаваме по 100 фирми наведнъж
        for i in range(start_id, start_id + 100):
            if i >= 100000: break
            
            company_id = f"{i:05}"
            target_url = f"https://www.jobs.bg/company/{company_id}/jobs"
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ID: {company_id}")
            
            driver.get(target_url)
            time.sleep(5) # Твоите златни 5 секунди
            
            try:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                company_name_tag = soup.find('h2', class_='center-content')
                
                if not company_name_tag:
                    save_progress(i)
                    continue
                
                company_name = company_name_tag.get_text(strip=True)
                job_cards = soup.find_all('li', attrs={'additional-params': True})
                
                if job_cards:
                    parsing_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for card in job_cards:
                        try:
                            params = json.loads(card['additional-params'])
                            date_posted = params.get('list_datetime', '').split(' ')[0]
                            title_div = card.find('div', class_='card-title')
                            position = title_div.find_all('span')[-1].get_text(strip=True)
                            subtitle_div = card.find('div', class_='card-info card__subtitle')
                            city = subtitle_div.get_text(separator=' ', strip=True).split(';')[0].split(',')[0].strip()
                            
                            save_entry([date_posted, position, city, target_url, parsing_timestamp, company_name])
                        except:
                            continue
                    print(f"  [+] Saved jobs for {company_name}")
                
                save_progress(i)
            except Exception as e:
                print(f"Error at ID {company_id}: {e}")
                continue

    finally:
        driver.quit()

if __name__ == "__main__":
    run_the_gauntlet()
