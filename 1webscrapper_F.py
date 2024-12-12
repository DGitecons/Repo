import os
import requests
from bs4 import BeautifulSoup
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configurações e caminhos
url_news = "https://www.itecons.uc.pt/articles"
url_events = "https://www.itecons.uc.pt/"
json_news_path = r"C:\\xampp\\htdocs\\NEWS\\prodWidgets\\webscrapper\\itecons_news.json"
json_events_path = r"C:\\xampp\\htdocs\\NEWS\\prodWidgets\\webscrapper\\itecons_next.json"

# Headers para o requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Parte 1: Web scraping dos artigos com BeautifulSoup
def scrape_news():
    try:
        response = requests.get(url_news, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a página de notícias: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    articles_data = []

    cards = soup.find_all("a", class_="card-link bg-secondary")
    for card in cards:
        if len(articles_data) >= 8:  # Limitar a 8 artigos
            break

        try:
            img_tag = card.find("img", class_="card-img")
            img_url = f"https://www.itecons.uc.pt{img_tag['src']}" if img_tag and 'src' in img_tag.attrs else "N/A"

            overlay_div = card.find("div", class_="card-img-overlay-bottom")
            title_tag = overlay_div.find("h6", class_="card-title text-uppercase text-truncate font-size-sm font-weight-bold")
            title = title_tag.text.strip() if title_tag else "N/A"

            desc_tag = overlay_div.find("p", class_="card-text text-uppercase font-weight-light")
            description = desc_tag.text.strip() if desc_tag else "N/A"

            if title != "N/A" or description != "N/A":
                articles_data.append({
                    "imagem": img_url,
                    "titulo": title,
                    "descricao": description
                })

        except Exception as e:
            print(f"Erro ao processar um card: {str(e)}")

    os.makedirs(os.path.dirname(json_news_path), exist_ok=True)
    with open(json_news_path, "w", encoding="utf-8") as jsonfile:
        json.dump(articles_data, jsonfile, ensure_ascii=False, indent=4)

    print(f"Notícias exportadas para '{json_news_path}'.")

# Parte 2: Web scraping dos eventos com Selenium
def scrape_events():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(url_events)
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.slick-slide')))

        title = driver.find_element(By.CSS_SELECTOR, 'div.text-uppercase.text-center.text-primary.font-weight-light.mb-0.h2').text.strip()
        events = driver.find_elements(By.CSS_SELECTOR, 'div.slick-slide')

        event_data = []
        for event in events:
            try:
                date_div = event.find_element(By.CSS_SELECTOR, 'div.card-date')
                date = date_div.find_element(By.CSS_SELECTOR, 'div.font-weight-bold').text.strip() + " " + date_div.find_element(By.CSS_SELECTOR, 'small').text.strip()

                img = event.find_element(By.CSS_SELECTOR, 'img.card-img-top').get_attribute('src')
                subtitle = event.find_element(By.CSS_SELECTOR, 'div.card-title').text.strip()

                try:
                    description = event.find_element(By.CSS_SELECTOR, 'p.card-text.text-uppercase.font-weight-light.font-size-sm').text.strip()
                except Exception:
                    description = ""

                event_data.append({
                    "date": date,
                    "img": img,
                    "subtitle": subtitle,
                    "description": description
                })

            except Exception as e:
                print(f"Erro ao processar evento: {e}")

        data = {
            "title": title,
            "events": event_data
        }

        with open(json_events_path, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)

        print(f"Eventos exportados para '{json_events_path}'.")

    finally:
        driver.quit()

# Executar as funções
if __name__ == "__main__":
    scrape_news()
    scrape_events()
