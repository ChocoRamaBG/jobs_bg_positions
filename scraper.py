import os
import time
import json
import csv
from datetime import datetime
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

# Файлове в репото
LINKS_FILE = "links.txt"
PROGRESS_FILE = "last_index.txt"
MASTER_CSV = "master_jobs.csv"

def get_last_index():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            try: return int(f.read().strip())
            except: return 0
    return 0

def save_progress(index):
    with open(PROGRESS_FILE, 'w') as f:
        f.write(str(index))

def save_entry(row):
    file_exists = os.path.isfile(MASTER_CSV)
    with open(MASTER_CSV, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Date Posted', 'Position', 'City', 'Source Link', 'Parsing Timestamp', 'Company Name'])
        writer.writerows([row])

def run_the_gauntlet():
    if not os.path.exists(LINKS_FILE):
        print("What the fuck, шефе! Къде е links.txt?")
        return

    with open(LINKS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"--- STARTING LIST-STALKER PROTOCOL ({len(urls)} links) ---")
    
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    try:
        # Ползваме версия 144 за GitHub Runners
        driver = uc.Chrome(options=options, version_main=144)
        
        start_idx = get_last_index()
        # Взимаме следващите 20 линка на всяко пускане, за да не ни резнат
        work_batch = urls[start_idx : start_idx + 20]

        for i, target_url in enumerate(work_batch):
            current_total_idx = start_idx + i
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing: {target_url}")
            
            driver.get(target_url)
            
            # Логика за изчакване
            if i == 0:
                print("First link of the batch: Waiting 10s for stability...")
                time.sleep(10)
            else:
                print("Wait 5s...")
                time.sleep(5)
            
            try:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                company_tag = soup.find('h2', class_='center-content')
                
                if not company_tag:
                    print(f"  [-] No company found at {target_url}. Skipping.")
                    save_progress(current_total_idx + 1)
                    continue
                
                company_name = company_tag.get_text(strip=True)
                job_cards = soup.find_all('li', attrs={'additional-params': True})
                
                if job_cards:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for card in job_cards:
                        try:
                            params = json.loads(card['additional-params'])
                            date = params.get('list_datetime', '').split(' ')[0]
                            pos = card.find('div', class_='card-title').find_all('span')[-1].get_text(strip=True)
                            city = card.find('div', class_='card-info card__subtitle').get_text(separator=' ', strip=True).split(';')[0].strip()
                            
                            save_entry([date, pos, city, target_url, now, company_name])
                        except: continue
                    print(f"  [+] Saved {len(job_cards)} jobs for {company_name}")
                
                # Записваме прогреса след всяка успешна фирма
                save_progress(current_total_idx + 1)
                
            except Exception as e:
                print(f"Error parsing {target_url}: {e}")
                continue

        # Ако сме стигнали края на списъка, рестартираме за следващия цикъл (по желание)
        if start_idx + 20 >= len(urls):
            print("Reached end of links.txt. Resetting index to 0.")
            save_progress(0)

    except Exception as e:
        print(f"CRITICAL SYSTEM FAILURE: {e}")
    finally:
        if 'driver' in locals(): driver.quit()

if __name__ == "__main__":
    run_the_gauntlet()
