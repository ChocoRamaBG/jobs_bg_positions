import os
import time
import json
import csv
from datetime import datetime
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

# --- THE CLOUD PATHS ---
# Изходните файлчовци отиват в script/
try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

# Слагаме логовете в подпапка, за да не стане мазало
LOG_DIR = os.path.join(output_dir, "page_dumps")
os.makedirs(LOG_DIR, exist_ok=True)

LINKS_FILE = os.path.join(output_dir, "links.txt")
PROGRESS_FILE = os.path.join(output_dir, "last_index.txt")
MASTER_CSV = os.path.join(output_dir, "master_jobs.csv")

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
        print("What the fuck, шефе! Няма links.txt в репото. Пълен andibul carrot!")
        return

    with open(LINKS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"--- STARTING CLOUD-STALKER PROTOCOL ({len(urls)} линкочовци) ---")
    
    options = uc.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    try:
        driver = uc.Chrome(options=options, version_main=144)
        
        start_idx = get_last_index()
        work_batch = urls[start_idx : start_idx + 20]

        for i, target_url in enumerate(work_batch):
            current_total_idx = start_idx + i
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing: {target_url}")
            
            driver.get(target_url)
            
            # Малко почивка, че тоя Cloudflare е злобен като свекърва
            wait_time = 10 if i == 0 else 5
            time.sleep(wait_time)
            
            page_src = driver.page_source
            
            # --- DEBUG DUMP ---
            # Запазваме страницата, за да видиш какъв скандалчовци стават вътре
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"page_{current_total_idx}_{timestamp}.html"
            with open(os.path.join(LOG_DIR, filename), "w", encoding="utf-8") as f:
                f.write(page_src)
            print(f"  [!] Snapshot saved: {filename}")
            # ------------------
            
            if "Проверка за това, че не сте робот" in page_src or "Cloudflare" in page_src:
                print("Hell, we got busted! GitHub IP-то е блокирано. Малини, къпини, все тая - спираме.")
                break 
            
            try:
                soup = BeautifulSoup(page_src, 'html.parser')
                company_tag = soup.find('h2', class_='center-content')
                
                if not company_tag:
                    print(f"  [-] No company found. Dead rizz. Провери файлчовци в {LOG_DIR}")
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
                            city = card.find('div', class_='card-info card__subtitle').get_text(separator=' ', strip=True).split(',')[0].strip()
                            
                            save_entry([date, pos, city, target_url, now, company_name])
                        except Exception:
                            continue
                            
                    print(f"  [+] Saved {len(job_cards)} jobs for {company_name}")
                
                save_progress(current_total_idx + 1)
                
            except Exception as e:
                print(f"Error parsing: {e}")
                continue

        if start_idx + 20 >= len(urls):
            print("Reached end of links.txt. Resetting index to 0.")
            save_progress(0)

    except Exception as e:
        print(f"CRITICAL SYSTEM FAILURE: {e}")
    finally:
        if 'driver' in locals(): driver.quit()

if __name__ == "__main__":
    run_the_gauntlet()
