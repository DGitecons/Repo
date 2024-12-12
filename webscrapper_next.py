from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json

# Configuração do Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Para rodar sem abrir o navegador
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# URL do site de onde queremos extrair as informações
url = 'https://www.itecons.uc.pt/'

# Acessar a página
driver.get(url)

# Aguardar até que os eventos estejam visíveis na página
WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.slick-slide')))

# Extrair o título da seção de eventos
title = driver.find_element(By.CSS_SELECTOR, 'div.text-uppercase.text-center.text-primary.font-weight-light.mb-0.h2').text.strip()

# Localizar todos os eventos
events = driver.find_elements(By.CSS_SELECTOR, 'div.slick-slide')

# Lista para armazenar os eventos extraídos
event_data = []

# Loop para percorrer cada evento e extrair as informações
for event in events:
    event_info = {}

    try:
        # Extrair a data
        date_div = event.find_element(By.CSS_SELECTOR, 'div.card-date')
        date = date_div.find_element(By.CSS_SELECTOR, 'div.font-weight-bold').text.strip() + " " + date_div.find_element(By.CSS_SELECTOR, 'small').text.strip()

        # Extrair a imagem
        img = event.find_element(By.CSS_SELECTOR, 'img.card-img-top').get_attribute('src')

        # Extrair o subtítulo
        subtitle = event.find_element(By.CSS_SELECTOR, 'div.card-title').text.strip()

        # Tentar extrair o texto do elemento <p>
        try:
            description = event.find_element(By.CSS_SELECTOR, 'p.card-text.text-uppercase.font-weight-light.font-size-sm').text.strip()
        except Exception:
            description = ""  # Define a descrição como string vazia caso não seja encontrada

        # Adicionar as informações ao dicionário
        event_info['date'] = date
        event_info['img'] = img
        event_info['subtitle'] = subtitle
        event_info['description'] = description  # Sempre adiciona o parâmetro description

        # Adicionar o evento à lista de dados
        event_data.append(event_info)

    except Exception as e:
        print(f"Erro ao processar evento: {e}")

# Criar o dicionário final com o título e os eventos
data = {
    'title': title,
    'events': event_data
}

# Caminho para salvar o arquivo JSON
output_path = r'C:\\xampp\\htdocs\\NEWS\\prodWidgets\\webscrapper\\itecons_next.json'

# Salvar as informações em um arquivo JSON
with open(output_path, 'w', encoding='utf-8') as json_file:
    json.dump(data, json_file, indent=4, ensure_ascii=False)

# Fechar o navegador
driver.quit()

print(f"Dados salvos em {output_path}")
