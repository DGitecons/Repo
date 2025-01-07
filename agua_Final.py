from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import requests
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itertools import groupby

# Configuração do WebDriver (Chromedriver)
chrome_options = Options()
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.98 Safari/537.36')
chrome_options.add_argument('--headless')  # Executa em modo headless
driver = webdriver.Chrome(options=chrome_options)

# Credenciais de login
username = "itecons@itecons.uc.pt"
password = "Telemetria.2021"

# Configuração do ThingsBoard
thingsboard_config = {
    'base_url': 'https://thingsboard.itecons.pt',
    'device_token': '1r6buwEHSYQYQfVEHlP7',
    'device_id': '67c30010-cce3-11ef-a0ee-df46eee9b5b2',
    'username': 'tiago.jesus@itecons.uc.pt',
    'password': 'YNKgRp9k'
}

# Configuração do e-mail
email_config = {
    'smtp_server': 'mail.uc.pt',
    'smtp_port': 465,
    'sender_email': 'itecons.noreply@itecons.uc.pt',
    'sender_password': 'Gkmb3(yehK!mn',
    'recipient_email': 'diogo.gerardo@itecons.uc.pt'
}

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Headers para autenticação no ThingsBoard
headers = {
    'X-Authorization': f'Bearer {thingsboard_config["device_token"]}',
    'Content-Type': 'application/json'
}

# Função para verificar se o e-mail pode ser enviado
def can_send_email():
    now = datetime.now()
    # Verifica se é um dia útil (segunda a sexta-feira)
    if now.weekday() >= 5:  # 5 = sábado, 6 = domingo
        return False
    # Verifica se o horário está entre 10h e 11h
    if now.hour != 10:  # Só permite enviar entre 10h e 11h
        return False
    return True

# Função para enviar e-mail
def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = email_config['sender_email']
    msg['To'] = email_config['recipient_email']
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.sendmail(email_config['sender_email'], email_config['recipient_email'], msg.as_string())
        logging.info("E-mail enviado com sucesso!")
    except Exception as e:
        logging.error(f"Erro ao enviar e-mail: {e}")

# Função para gerar o corpo do e-mail
def generate_email_body(exceeded_sensors, start_date, end_date, max_hourly_consumption):
    date_range = f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}"
    
    if len(exceeded_sensors) == 0:
        subject = f"✅ RELATÓRIO {date_range}: Nenhum Registo Excedeu o Limite de Consumo"
        message_body = f"RELATÓRIO DE CONSUMO DE ÁGUA\n"
        message_body += f"\nPeríodo de Análise: {start_date.strftime('%Y-%m-%d %H:%M')} até {end_date.strftime('%Y-%m-%d %H:%M')}\n"
        message_body += f"\nLimite Máximo por Hora: {max_hourly_consumption} L\n\n"
        message_body += "NENHUM REGISTO EXCEDEU O LIMITE DE CONSUMO NO PERÍODO ANALISADO.\n"
    else:
        subject = f"⚠️ RELATÓRIO {date_range}: {len(exceeded_sensors)} Registos Excederam o Limite de Consumo"
        message_body = f"RELATÓRIO DE CONSUMO DE ÁGUA\n\n"
        message_body += f"Período de Análise: {start_date.strftime('%Y-%m-%d %H:%M')} até {end_date.strftime('%Y-%m-%d %H:%M')}\n"
        message_body += f"\nLimite Máximo por Hora: {max_hourly_consumption} L\n\n"
        message_body += "Registos QUE EXCEDERAM O LIMITE DE CONSUMO:\n"
        
        # Agrupa os sensores por ID e ordena as ocorrências
        sorted_sensors = sorted(exceeded_sensors, key=lambda x: x['sensor_id'])
        for sensor_id, group in groupby(sorted_sensors, key=lambda x: x['sensor_id']):
            message_body += f"\nSensor ID: {sensor_id}\n"
            message_body += "Ocorrências:\n"
            for sensor in group:
                message_body += f"- Timestamp: {sensor['timestamp']}\n"
                message_body += f"  Consumo Horário: {sensor['consumo']} L\n"
                message_body += f"  Consumo Acumulado Diário: {sensor.get('consumo_acumulado_dia', 'N/A')} L\n"
                message_body += "------------------------------------------\n"
    
    return subject, message_body

# Função para obter o último timestamp armazenado no ThingsBoard
def get_latest_timestamp():
    try:
        url = f"{thingsboard_config['base_url']}/api/plugins/telemetry/DEVICE/{thingsboard_config['device_id']}/values/timeseries"
        params = {
            'keys': 'timestamp',
            'limit': 1,
            'agg': 'NONE'
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 401:
            logging.info('Token expirado, obtendo novo token')
            get_new_token()
            response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if 'timestamp' in data and data['timestamp']:
                return datetime.fromisoformat(data['timestamp'][0]['value'])
        return None
    except Exception as e:
        logging.error(f"Erro ao obter o último timestamp: {e}")
        return None

# Função para obter um novo token de autenticação
def get_new_token():
    try:
        url = f"{thingsboard_config['base_url']}/api/auth/login"
        payload = {
            'username': thingsboard_config['username'],
            'password': thingsboard_config['password']
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            token = response.json()['token']
            headers['X-Authorization'] = f'Bearer {token}'
            logging.info('Novo token obtido com sucesso')
        else:
            logging.error(f"Falha ao obter novo token: {response.status_code}")
    except Exception as e:
        logging.error(f"Erro ao obter novo token: {e}")

# Função para enviar dados ao ThingsBoard
def send_to_thingsboard(sensor_data):
    try:
        url = f"{thingsboard_config['base_url']}/api/v1/{thingsboard_config['device_token']}/telemetry"
        dt = datetime.strptime(sensor_data['timestamp'], '%d/%m/%Y %H:%M')
        
        # Converte o timestamp para milissegundos
        ts = int(dt.timestamp() * 1000)
        
        # Prepara o payload
        telemetry_payload = {
            "ts": ts,
            "values": {
                "sensor_id": sensor_data['sensor_id'],
                "hourly_consumption": sensor_data['consumo'],
                "total_consumption": sensor_data['total_consumo'],
                "daily_accumulated_consumption": sensor_data['consumo_acumulado_dia'],
                "timestamp": dt.isoformat()  # Adiciona o timestamp no payload
            }
        }
        
        # Envia os dados
        response = requests.post(url, json=telemetry_payload, headers=headers, timeout=10)
        if response.status_code == 200:
            logging.info(f"Dados enviados com sucesso para o ThingsBoard: {sensor_data}")
        else:
            logging.error(f"Falha ao enviar dados: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao enviar dados para o ThingsBoard: {e}")

# Função principal
def main():
    try:
        # Acessa a página de login
        login_url = "https://www.goreadycloud02.com/waterlog/Account/Login?ReturnUrl=%2Fwaterlog%2FSensor%2FDaily"
        driver.get(login_url)
        time.sleep(10)

        # Preenche o campo de username
        username_field = driver.find_element(By.ID, "Username")
        username_field.send_keys(username)

        # Preenche o campo de password
        password_field = driver.find_element(By.ID, "Password")
        password_field.send_keys(password)

        # Clica no botão de login
        login_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Log in']")
        login_button.click()
        time.sleep(10)

        # Navega para a página de consumo horário
        hourly_url = "https://www.goreadycloud02.com/waterlog/Sensor/Hourly"
        driver.get(hourly_url)
        time.sleep(10)

        # Seleciona a opção "1,000" no dropdown
        dropdown = driver.find_element(By.NAME, "DataTables_Table_0_length")
        dropdown.click()
        option_1000 = driver.find_element(By.XPATH, "//option[@value='1000']")
        option_1000.click()
        time.sleep(10)

        # Localiza todas as linhas da tabela
        rows = driver.find_elements(By.XPATH, "//tbody/tr")
        rows.reverse()

        # Variáveis para o relatório
        max_hourly_consumption = 500  # Limite máximo de consumo por hora
        exceeded_sensors = []  # Lista para armazenar sensores que excederam o limite
        now = datetime.now()  # Data e hora atuais

        # Obtém o último timestamp armazenado no ThingsBoard
        latest_timestamp = get_latest_timestamp()

        # Variáveis para cálculo do consumo acumulado diário
        current_day = None
        daily_accumulated = 0.0

        # Variáveis para calcular o período de análise
        first_timestamp = None
        last_timestamp = None

        # Itera sobre cada linha e extrai os valores das células
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 5:
                sensor_id = cells[0].text
                timestamp = cells[2].text
                hourly_consumption = float(str(cells[3].text).replace(',', ''))
                total_consumption = float(str(cells[4].text).replace(',', ''))

                # Converte o timestamp para um objeto datetime
                dt = datetime.strptime(timestamp, '%d/%m/%Y %H:%M')

                # Verifica se o timestamp é mais recente que o último armazenado
                if latest_timestamp and dt <= latest_timestamp:
                    continue  # Ignora registros antigos

                # Atualiza o primeiro e o último timestamp do período de análise
                if first_timestamp is None:
                    first_timestamp = dt
                last_timestamp = dt

                # Verifica se o dia mudou
                day = dt.date()
                if current_day is None:
                    current_day = day
                elif day != current_day:
                    # Reinicia o acumulado diário se o dia mudar
                    daily_accumulated = 0.0
                    current_day = day

                # Acumula o consumo horário no consumo diário
                daily_accumulated += hourly_consumption

                # Verifica se o consumo horário excedeu o limite
                if hourly_consumption > max_hourly_consumption:
                    exceeded_sensors.append({
                        'sensor_id': sensor_id,
                        'timestamp': timestamp,
                        'consumo': hourly_consumption,
                        'consumo_acumulado_dia': daily_accumulated  # Adiciona o consumo acumulado diário
                    })

                # Prepara os dados para envio ao ThingsBoard
                sensor_data = {
                    'sensor_id': sensor_id,
                    'timestamp': timestamp,
                    'consumo': hourly_consumption,
                    'total_consumo': total_consumption,
                    'consumo_acumulado_dia': daily_accumulated
                }

                # Envia os dados para o ThingsBoard
                send_to_thingsboard(sensor_data)

        # Gera o corpo do e-mail
        if first_timestamp is not None and last_timestamp is not None:
            subject, message_body = generate_email_body(exceeded_sensors, first_timestamp, last_timestamp, max_hourly_consumption)
        else:
            # Se não houver novos dados, usa o último timestamp armazenado como período de análise
            if latest_timestamp:
                subject = "✅ RELATÓRIO - CONSUMO DE ÁGUA: Nenhum Novo Dado Processado"
                message_body = f"RELATÓRIO DE CONSUMO DE ÁGUA\n"
                message_body += f"\nPeríodo de Análise: {latest_timestamp.strftime('%Y-%m-%d %H:%M')} até {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                message_body += f"\nLimite Máximo por Hora: {max_hourly_consumption} L\n\n"
                message_body += "NENHUM NOVO DADO FOI PROCESSADO NO PERÍODO ANALISADO.\n"
            else:
                subject = "✅ RELATÓRIO - CONSUMO DE ÁGUA: Nenhum Dado Disponível"
                message_body = "NENHUM DADO FOI PROCESSADO OU ARMAZENADO.\n"

        # Verifica se o e-mail pode ser enviado
        if can_send_email():
            # Envia o e-mail
            send_email(subject, message_body)
        else:
            logging.info("Fora do horário permitido para envio de e-mails (10h-11h em dias úteis).")

    except Exception as e:
        logging.error(f"Ocorreu um erro: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
