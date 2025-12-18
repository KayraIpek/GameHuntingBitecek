from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

# --- AYARLAR ---
CACHE_TIMEOUT = 300  # 300 saniye (5 dakika) boyunca veriyi hafızada tut
cache = {
    'steam': {'data': [], 'timestamp': 0},
    'itch': {'data': [], 'timestamp': 0},
    'epic': {'data': [], 'timestamp': 0}
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def get_steam_data():
    # Cache kontrolü
    if time.time() - cache['steam']['timestamp'] < CACHE_TIMEOUT and cache['steam']['data']:
        print("Steam verisi önbellekten çekildi.")
        return cache['steam']['data']

    url = "https://store.steampowered.com/search/?specials=1&l=turkish"
    games_list = []
    print("\n--- Steam Taranıyor (Canlı) ---")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.select('#search_resultsRows a')
            
            for row in rows[:15]: # Sayıyı 15'e çıkardık
                try:
                    title = row.find('span', class_='title').text.strip()
                    price_div = row.find('div', class_='discount_final_price')
                    price = price_div.text.strip() if price_div else "Fiyat Yok"
                    link = row.get('href') # Linki alıyoruz
                    
                    img_tag = row.find('img')
                    img_url = img_tag.get('src') or img_tag.get('srcset', '').split(' ')[0] if img_tag else ""
                    
                    games_list.append({'name': title, 'price': price, 'image': img_url, 'link': link, 'store': 'steam'})
                except: continue
            
            # Cache güncelle
            cache['steam']['data'] = games_list
            cache['steam']['timestamp'] = time.time()

    except Exception as e:
        print(f"Steam Hatası: {e}")
    return games_list

def get_itchio_data():
    if time.time() - cache['itch']['timestamp'] < CACHE_TIMEOUT and cache['itch']['data']:
        print("Itch.io verisi önbellekten çekildi.")
        return cache['itch']['data']

    urls = ["https://itch.io/games/on-sale", "https://itch.io/games"]
    games_list = []
    print("\n--- Itch.io Taranıyor (Canlı) ---")

    for url in urls:
        if len(games_list) > 0: break 
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                cells = soup.find_all('div', class_='game_cell')
                
                for cell in cells[:15]:
                    try:
                        title_tag = cell.find('a', class_='title')
                        if not title_tag: continue
                        
                        title = title_tag.text.strip()
                        link = title_tag.get('href') # Linki al
                        # Eğer link tam url değilse tamamla
                        if link and not link.startswith('http'):
                            link = f"https://itch.io{link}"

                        price_tag = cell.find('div', class_='price_value') or cell.find('div', class_='sale_tag')
                        price = price_tag.text.strip() if price_tag else "Göz Atın"
                        
                        img_div = cell.find('div', class_='game_thumb')
                        img_url = img_div.get('data-background_image', '') if img_div else ""
                        
                        games_list.append({'name': title, 'price': price, 'image': img_url, 'link': link, 'store': 'itch'})
                    except: continue

                cache['itch']['data'] = games_list
                cache['itch']['timestamp'] = time.time()
        except Exception as e:
            print(f"Itch URL Hatası ({url}): {e}")
            
    return games_list

def get_epic_data():
    if time.time() - cache['epic']['timestamp'] < CACHE_TIMEOUT and cache['epic']['data']:
        print("Epic Games verisi önbellekten çekildi.")
        return cache['epic']['data']

    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    games_list = []
    print("\n--- Epic Games Taranıyor (Canlı) ---")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            elements = data['data']['Catalog']['searchStore']['elements']
            
            for game in elements:
                promotions = game.get('promotions')
                if promotions and promotions.get('promotionalOffers'):
                    offers = promotions['promotionalOffers']
                    if offers and len(offers) > 0:
                        title = game['title']
                        
                        # Epic Link Oluşturma
                        slug = game.get('productSlug') or game.get('urlSlug')
                        link = f"https://store.epicgames.com/p/{slug}" if slug else "https://store.epicgames.com/free-games"

                        img_url = ""
                        for img in game.get('keyImages', []):
                            if img.get('type') in ['Thumbnail', 'OfferImageWide']:
                                img_url = img.get('url')
                                break
                        games_list.append({'name': title, 'price': 'ÜCRETSİZ', 'image': img_url, 'link': link, 'store': 'epic'})
            
            cache['epic']['data'] = games_list
            cache['epic']['timestamp'] = time.time()
    except Exception as e:
        print(f"Epic Hatası: {e}")
    return games_list

@app.route('/')
def index():
    steam = get_steam_data()
    itch = get_itchio_data()
    epic = get_epic_data()
    
    # İstatistikler
    stats = {
        'steam_count': len(steam),
        'itch_count': len(itch),
        'epic_count': len(epic),
        'last_update': time.strftime('%H:%M:%S')
    }
    
    return render_template('index.html', steam_games=steam, itch_games=itch, epic_games=epic, stats=stats)

if __name__ == '__main__':
    app.run(debug=True, port=5000)