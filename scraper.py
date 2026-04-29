import os
import time
import random
import json
import csv
import requests
from datetime import datetime
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

# --- THE CLOUD PATHS ---
try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

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

# БОКЛУЧЕ, ЕТО ТИ КЛОШАРСКИТЕ ПРОКСИЧОВЦИ!
def get_free_proxies():
    print("  [🗑️] Ровиме в кофата за безплатни проксичовци...")
    try:
        # Теглиме списък с безплатни проксита (пълен леш са, ама нали си скъсан)
        res = requests.get("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", timeout=10)
        if res.status_code == 200:
            proxies = res.text.strip().split('\n')
            # Взимаме само няколко случайни, че иначе ше чакаме до второ пришествие
            random.shuffle(proxies)
            return proxies[:50] 
    except Exception as e:
        print(f"  [❌] Hell, дори кофата за боклук е празна: {e}")
    return []

def run_the_gauntlet():
    if not os.path.exists(LINKS_FILE):
        print("What the fuck, шефе! Няма links.txt. Пълен andibul carrot!")
        return

    with open(LINKS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"--- STARTING CLOUD-STALKER PROTOCOL ({len(urls)} линкочовци) ---")
    
    # Взимаме проксичовци за бедняци
    free_proxies = get_free_proxies()
    if not free_proxies:
        print("Няма проксита, Гащник. Ше пробваме на голо!")
        free_proxies = [None] # Слагаме None, за да мине поне един път без прокси
    
    start_idx = get_last_index()
    work_batch = urls[start_idx : start_idx + 20]

    for i, target_url in enumerate(work_batch):
        current_total_idx = start_idx + i
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Processing: {target_url}")
        
        success = False
        
        # Въртиме през скапаните проксичовци, докато някое не хване дикиш
        for proxy in free_proxies:
            options = uc.ChromeOptions()
            options.add_argument("--headless") 
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
            
            if proxy:
                print(f"  [🔄] Пробваме с клошарско прокси: {proxy}")
                options.add_argument(f'--proxy-server=http://{proxy}')
            
            driver = None
            try:
                # Батко чатко ти остави 147, за да не гърмят пак тъпите еррорчовци!
                driver = uc.Chrome(options=options, version_main=147)
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                })

                # Слагаме timeout, че тия безплатни проксита забиват като дядо ти след две ракии
                driver.set_page_load_timeout(45)
                
                try:
                    driver.get(target_url)
                except Exception as e:
                    print(f"  [☠️] Проксито умря при зареждането. Сменяме го!")
                    if driver: driver.quit()
                    continue # Скачаме на следващото прокси
                
                # Рандомизирани паузички
                wait_time = random.uniform(20.0, 35.0) if i == 0 else random.uniform(8.0, 16.0)
                print(f"  [⏳] Чакаме {wait_time:.2f} секунди...")
                time.sleep(wait_time)
                
                page_src = driver.page_source
                timestamp = datetime.now().strftime("%H%M%S")
                
                html_filename = f"page_{current_total_idx}_{timestamp}.html"
                with open(os.path.join(LOG_DIR, html_filename), "w", encoding="utf-8") as f:
                    f.write(page_src)
                    
                screenshot_filename = f"screenshot_{current_total_idx}_{timestamp}.png"
                driver.save_screenshot(os.path.join(LOG_DIR, screenshot_filename))
                
                if "Проверка за това, че не сте робот" in page_src or "Cloudflare" in page_src or "Достъпът е временно ограничен" in page_src:
                    print(f"  [🛑] Блъснахме се в стената! Това прокси е в черния списък. Малини, къпини, все тая.")
                    if driver: driver.quit()
                    continue # Скачаме на следващото прокси
                
                # Ако сме стигнали дотук, значи проксито май работи!
                try:
                    soup = BeautifulSoup(page_src, 'html.parser')
                    company_tag = soup.find('h2', class_='center-content')
                    
                    if not company_tag:
                        print(f"  [-] Няма компания. Dead rizz. Виж {html_filename}")
                        # Може да е някаква друга грешка, не е нужно да сменяме проксито веднага
                    else:
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
                            print(f"  [+] 🤑 УСПЕХ! Спасихме {len(job_cards)} обяви за {company_name}")
                            success = True
                            
                except Exception as e:
                    print(f"Error parsing: {e}")
                
                # Ако сме успели, махаме се от цикъла с прокситата и продължаваме със следващия линк
                if success:
                    save_progress(current_total_idx + 1)
                    if driver: driver.quit()
                    break 

            except Exception as e:
                print(f"  [⚠️] Проблемче с браузърчето или проксито: {e}")
            finally:
                if driver: 
                    try: driver.quit()
                    except: pass
        
        if not success:
            print(f"  [💀] Всички безплатни проксичовци се осраха за тоя линк! Пълен andibul carrot!")
            save_progress(current_total_idx + 1) # Прескачаме го, че ше си изгнием тука

    if start_idx + 20 >= len(urls):
        print("End of list. Resetting index.")
        save_progress(0)

if __name__ == "__main__":
    # Щото сме скъсаняци, ще ни трябва библиотеката requests
    # pip install requests
    run_the_gauntlet()
