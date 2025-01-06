# Primeiro, instale o Selenium e o Chrome WebDriver
# pip install selenium
# Para Raspberry Pi: sudo apt-get install chromium-chromedriver

import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import getpass

def configure_chrome():
    """Configura as opções do Chrome"""
    options = Options()
    # Opções úteis para debugging e performance
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Descomente a linha abaixo para rodar em modo headless (sem interface gráfica)
    # options.add_argument('--headless')
    return options

def login(browser, username_text="admin"):
    """Realiza o login no site"""
    browser.find_element(By.LINK_TEXT, "Login").click()
    time.sleep(2)  # Espera a página carregar
    
    username = browser.find_element(By.ID, "username")
    password = browser.find_element(By.ID, "password")
    
    username.send_keys(username_text)
    senha = getpass.getpass("Digite sua senha: ")
    password.send_keys(senha)
    
    browser.find_element(By.CSS_SELECTOR, "input.btn-primary").click()
    time.sleep(2)  # Espera o login completar

def scrape_quotes(browser, arquivo_saida="citacoes_scraping.csv"):
    """Faz o scraping das citações e autores"""
    with open(arquivo_saida, "w", newline='', encoding='utf-8') as arquivo:
        writer = csv.writer(arquivo)
        writer.writerow(["CITAÇÃO", "AUTOR"])
        
        pagina = 1
        while True:
            print(f"\nColetando dados da página {pagina}")
            
            # Encontra todas as citações e autores na página atual
            citacoes = browser.find_elements(By.CLASS_NAME, "text")
            autores = browser.find_elements(By.CLASS_NAME, "author")
            
            # Salva os dados no CSV
            for citacao, autor in zip(citacoes, autores):
                texto_citacao = citacao.text.strip('"').strip('"')  # Remove aspas
                texto_autor = autor.text
                print(f"Citação de {texto_autor} salva!")
                writer.writerow([texto_citacao, texto_autor])
            
            try:
                # Tenta ir para a próxima página
                proxima = browser.find_element(By.PARTIAL_LINK_TEXT, "Next")
                proxima.click()
                time.sleep(2)  # Espera a nova página carregar
                pagina += 1
            except NoSuchElementException:
                print("\nTodas as páginas foram processadas!")
                break

def main():
    """Função principal que executa o scraping"""
    try:
        # Configuração e inicialização do navegador
        print("Iniciando o scraping...")
        options = configure_chrome()
        browser = webdriver.Chrome(options=options)
        
        # Acessa o site
        browser.get("http://quotes.toscrape.com")
        print("Site acessado com sucesso!")
        
        # Realiza o login
        login(browser)
        print("Login realizado com sucesso!")
        
        # Faz o scraping
        scrape_quotes(browser)
        print("Scraping finalizado com sucesso!")
        
    except Exception as e:
        print(f"Ocorreu um erro: {str(e)}")
    
    finally:
        # Sempre fecha o navegador ao finalizar
        browser.quit()
        print("Navegador fechado.")

if __name__ == "__main__":
    main()
