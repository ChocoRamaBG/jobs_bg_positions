import os
import time
import json
import csv
from datetime import datetime
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

# The Holy Output Folder
OUTPUT_DIR = "script"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Входният файл си стои в root-а, но изходните логчовци и записчовци отиват в script/
LINKS_FILE = "links.txt"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "last_index.txt")
MASTER_CSV = os.path.join(OUTPUT_DIR, "master_jobs.csv")

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
        print("What the fuck, шефе! Къде е links.txt? This is a complete андибул морков.")
        return

    with open(LINKS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"--- STARTING LOW-KEY STALKER PROTOCOL ({len(urls)} линкочовци) ---")
    
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    try:
        # Използваме v144 за GitHub
        driver = uc.Chrome(options=options, version_main=144)
        
        start_idx = get_last_index()
        work_batch = urls[start_idx : start_idx + 20]

        for i, target_url in enumerate(work_batch):
            current_total_idx = start_idx + i
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing: {target_url}")
            
            driver.get(target_url)
            
            if i == 0:
                print("First link of the batch: Waiting 10s for Skibidi-DOM stability...")
                time.sleep(10)
            else:
                print("Wait 5s...")
                time.sleep(5)
            
            page_src = driver.page_source
            
            # THE FIX: Проверяваме дали не са ни хванали като Гащник, ПРЕДИ да парсваме!
            if "Проверка за това, че не сте робот" in page_src or "Cloudflare" in page_src:
                print("Hell, we got busted! The IP is blocked.")
                print("Спираме тези скриптчовци, за да не маркираме линка като 'успешен'!")
                break # Прекратяваме луупа тук, за да НЕ записваме фалшив прогрес.
            
            try:
                soup = BeautifulSoup(page_src, 'html.parser')
                company_tag = soup.find('h2', class_='center-content')
                
                if not company_tag:
                    print(f"  [-] No company found at {target_url}. Skipping this dead rizz.")
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
                        except Exception as e:
                            # THE FIX: Никога не оставяй гол except, за да не плачеш после!
                            print(f"  [!] Card parsing error (Brainrot structure): {e}")
                            continue
                            
                    print(f"  [+] Saved {len(job_cards)} jobs for {company_name}")
                
                # Чак като сме минали успешно, сейфваме индекса
                save_progress(current_total_idx + 1)
                
            except Exception as e:
                print(f"Error parsing {target_url}: {e}")
                continue

        # Ресетваме прогреса, ако стигнем края
        if start_idx + 20 >= len(urls):
            print("Reached end of links.txt. Resetting index to 0. It's time to sleep.")
            save_progress(0)

    except Exception as e:
        print(f"CRITICAL SYSTEM FAILURE: {e}")
    finally:
        if 'driver' in locals(): driver.quit()

if __name__ == "__main__":
    run_the_gauntlet()
