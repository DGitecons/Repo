import os
import requests
from bs4 import BeautifulSoup
import json

# URL da página
url = "https://www.itecons.uc.pt/articles"

# Caminho completo para o arquivo JSON
json_file_path = "C:\\xampp\\htdocs\\NEWS\\prodWidgets\\webscrapper\\itecons_news.json"

# Headers para simular um navegador
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Realizar o pedido HTTP
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Erro ao acessar a página: {e}")
    exit()

# Fazer o parsing do HTML
soup = BeautifulSoup(response.text, "html.parser")

# Lista para armazenar os dados
articles_data = []

# Encontrar todos os cards
cards = soup.find_all("a", class_="card-link bg-secondary")

# Iterar pelos cards
for card in cards:
    if len(articles_data) >= 8:  # Limitar a 8 artigos
        break

    try:
        # Extrair a imagem
        img_tag = card.find("img", class_="card-img")
        img_url = f"https://www.itecons.uc.pt{img_tag['src']}" if img_tag and 'src' in img_tag.attrs else "N/A"

        # Encontrar a div overlay
        overlay_div = card.find("div", class_="card-img-overlay-bottom")
        
        # Extrair o título
        title_tag = overlay_div.find("h6", class_="card-title text-uppercase text-truncate font-size-sm font-weight-bold")
        title = title_tag.text.strip() if title_tag else "N/A"

        # Extrair a descrição
        desc_tag = overlay_div.find("p", class_="card-text text-uppercase font-weight-light")
        description = desc_tag.text.strip() if desc_tag else "N/A"

        # Adicionar os dados se foram encontrados
        if title != "N/A" or description != "N/A":
            article_data = {
                "imagem": img_url,
                "titulo": title,
                "descricao": description
            }
            articles_data.append(article_data)
            print(f"Artigo processado: {title}")

    except Exception as e:
        print(f"Erro ao processar um card: {str(e)}")
        continue

# Criar o diretório se não existir
os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

# Salvar os dados em formato JSON
with open(json_file_path, "w", encoding="utf-8") as jsonfile:
    json.dump(articles_data, jsonfile, ensure_ascii=False, indent=4)

print(f"\nDados exportados para '{json_file_path}'.")
print(f"Número de artigos encontrados: {len(articles_data)}")

# Imprimir o primeiro artigo para verificação
if articles_data:
    print("\nPrimeiro artigo encontrado:")
    print(json.dumps(articles_data[0], ensure_ascii=False, indent=2))
