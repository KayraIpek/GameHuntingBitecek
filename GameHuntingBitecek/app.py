from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime

app = Flask(__name__)

# --- ÖNBELLEK SORUNUNU ÇÖZEN AYARLAR (YENİ EKLENDİ) ---
# Bu ayarlar sayesinde HTML'de yaptığın değişiklikleri anında görürsün.
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# ------------------------------------------------------

# Tarayıcı gibi görünmek için gerekli kimlik bilgisi
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def get_steam_data():
    """Steam İndirimli Oyunları"""
    base_url = "https://store.steampowered.com/search/results/"
    games_list = []
    print("\n--- Steam Taranıyor ---")
    
    max_pages = 5  
    count_per_page = 50 
    start = 0
    page = 1

    while page <= max_pages:
        print(f"Steam Sayfa {page} taranıyor...")
        params = {'specials': 1, 'l': 'turkish', 'start': start, 'count': count_per_page, 'infinite': 1}
        
        try:
            response = requests.get(base_url, headers=HEADERS, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                html_content = data.get('results_html', '')
                soup = BeautifulSoup(html_content, 'html.parser')
                rows = soup.select('a.search_result_row')
                
                if not rows: break

                for row in rows:
                    try:
                        title = row.find('span', class_='title').text.strip()
                        price_div = row.find('div', class_='discount_final_price')
                        price = price_div.text.strip() if price_div else "Fiyat Yok"
                        link = row.get('href')
                        img_tag = row.find('img')
                        img_url = img_tag.get('src') if img_tag else ""
                        
                        games_list.append({'name': title, 'price': price, 'image': img_url, 'link': link, 'store': 'steam'})
                    except: continue
                
                start += count_per_page
                page += 1
                time.sleep(1) 
            else: break
        except Exception as e:
            print(f"Steam Hatası: {e}")
            break
            
    return games_list

def get_itchio_data():
    """Itch.io - Korumalı Mod"""
    base_url = "https://itch.io/games/on-sale"
    games_list = []
    print("\n--- Itch.io Taranıyor ---")

    max_pages = 5
    current_page = 1
    session = requests.Session()
    session.headers.update(HEADERS)

    while current_page <= max_pages:
        print(f"Itch.io Sayfa {current_page} taranıyor...")
        try:
            url = f"{base_url}?page={current_page}"
            response = session.get(url, timeout=20)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                cells = soup.find_all('div', class_='game_cell')
                
                if not cells: break
                
                for cell in cells:
                    try:
                        title_tag = cell.find('a', class_='title')
                        if not title_tag: continue
                        title = title_tag.text.strip()
                        link = title_tag.get('href')
                        if link and not link.startswith('http'): link = f"https://itch.io{link}"

                        price_tag = cell.find('div', class_='price_value') or cell.find('div', class_='sale_tag')
                        price = price_tag.text.strip() if price_tag else "İndirimde"
                        
                        img_div = cell.find('div', class_='game_thumb')
                        img_url = img_div.get('data-background_image', '') if img_div else ""
                        
                        games_list.append({'name': title, 'price': price, 'image': img_url, 'link': link, 'store': 'itch'})
                    except: continue
                
                current_page += 1
                time.sleep(3) 
            else: break

        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError):
            print(f"Itch.io Bağlantıyı Kesti (Sayfa {current_page} atlanıyor)")
            current_page += 1
            time.sleep(5)
            continue
        except requests.exceptions.Timeout:
            current_page += 1
            continue
        except Exception: break
            
    return games_list

def get_epic_data():
    """Epic Games - Gelişmiş Link Düzeltme Modu (404 Önleyici)"""
    games_list = []
    print("\n--- Epic Games Taranıyor ---")
    
    # --- 1. ÜCRETSİZ OYUNLAR ---
    try:
        response = requests.get("https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions", headers=HEADERS, timeout=10)
        if response.status_code == 200:
            elements = response.json()['data']['Catalog']['searchStore']['elements']
            print(f"Epic Ücretsiz: {len(elements)} öge bulundu.")
            
            for game in elements:
                promotions = game.get('promotions')
                if promotions and promotions.get('promotionalOffers') and len(promotions['promotionalOffers']) > 0:
                    title = game['title']
                    
                    # --- GELİŞMİŞ LİNK BULMA (Deep Search) ---
                    # 1. Önce standart slug'a bak
                    slug = game.get('productSlug')
                    
                    # 2. Boşsa, urlSlug'a bak
                    if not slug:
                        slug = game.get('urlSlug')
                    
                    # 3. Hala boşsa, gizli özelliklere (customAttributes) bak
                    if not slug:
                        for attr in game.get('customAttributes', []):
                            if attr.get('key') == 'com.epicgames.app.productSlug':
                                slug = attr.get('value')
                                break
                    
                    # --- LİNK OLUŞTURMA ---
                    if slug:
                        offer_type = game.get('offerType')
                        # Eğer bu bir paketse (Bundle) link yapısı farklıdır
                        if offer_type == 'BUNDLE':
                            link = f"https://store.epicgames.com/bundles/{slug}"
                        else:
                            link = f"https://store.epicgames.com/p/{slug}"
                    else:
                        # 4. HİÇBİR ŞEY BULUNAMADIYSA -> 404 YERİNE ANA LİSTEYE GİT
                        # Bu sayede kullanıcı hata sayfası görmez.
                        link = "https://store.epicgames.com/free-games"
                    # ----------------------------------------

                    img_url = ""
                    for img in game.get('keyImages', []):
                        if img.get('type') in ['Thumbnail', 'OfferImageWide', 'DieselStoreFrontWide']:
                            img_url = img.get('url')
                            break
                    games_list.append({'name': title, 'price': "ÜCRETSİZ", 'image': img_url, 'link': link, 'store': 'epic'})
    except Exception as e: print(f"Epic Hata: {e}")

    # --- 2. İNDİRİMLİ OYUNLAR (CheapShark) ---
    try:
        response = requests.get("https://www.cheapshark.com/api/1.0/deals?storeID=25&pageSize=20&sortBy=Savings", headers=HEADERS, timeout=10)
        if response.status_code == 200:
            for deal in response.json():
                if any(g['name'] == deal.get('title') for g in games_list): continue
                link = f"https://www.cheapshark.com/redirect?dealID={deal.get('dealID')}"
                price = f"${deal.get('normalPrice')} -> ${deal.get('salePrice')}"
                games_list.append({'name': deal.get('title'), 'price': price, 'image': deal.get('thumb'), 'link': link, 'store': 'epic'})
    except: pass
    
    return games_list
@app.route('/')
def index():
    steam = get_steam_data()
    itch = get_itchio_data()
    epic = get_epic_data()
    return render_template('index.html', steam_games=steam, itch_games=itch, epic_games=epic)

if __name__ == '__main__':
    # Port 5001'de çalıştırıyoruz
    app.run(debug=True, port=5001)

