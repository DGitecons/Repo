import os
import json
import smtplib
import requests
from email.message import EmailMessage
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
from datetime import datetime, timedelta
from itertools import groupby

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='water_log_alerts.log'
)

class WaterLogAlertSystem:
    def __init__(self, login_url, username, password, export_dir, max_hourly_consumption=500,
                 email_config=None, file_retention_days=7, thingsboard_config=None):
        self.login_url = login_url
        self.username = username
        self.password = password
        self.export_dir = export_dir
        self.max_hourly_consumption = max_hourly_consumption
        self.file_retention_days = file_retention_days
        self.night_start_hour = 21
        self.night_end_hour = 8
        self.alert_hour = 9
        
        self.email_config = email_config or {
            'smtp_server': 'mail.uc.pt',
            'smtp_port': 465,
            'sender_email': 'itecons.noreply@itecons.uc.pt',
            'sender_password': 'Gkmb3(yehK!mn',
            'recipient_email': 'diogo.gerardo@itecons.uc.pt'
        }
        
        self.thingsboard_config = thingsboard_config or {
            'base_url': 'https://thingsboard.itecons.pt',
            'device_token': 'KdE4HGTLQGmrkzakv3nv',
            'device_id': '63b6fd00-c117-11ef-a0ee-df46eee9b5b2',
            'username': 'tiago.jesus@itecons.uc.pt',
            'password': 'YNKgRp9k'
        }
        
        self.headers = {
            'Content-Type': 'application/json',
            'X-Authorization': None
        }
        self.get_new_token()

    def get_new_token(self):
        try:
            response = requests.post(
                f"{self.thingsboard_config['base_url']}/api/auth/login",
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                json={
                    "username": self.thingsboard_config['username'],
                    "password": self.thingsboard_config['password']
                }
            )
            token = response.json()["token"]
            self.headers['X-Authorization'] = f"Bearer {token}"
            logging.info("Successfully obtained new ThingsBoard token")
            return token
        except Exception as e:
            logging.error(f"Error getting new token: {e}")
            return None

    def get_latest_timestamp(self):
        try:
            url = f"{self.thingsboard_config['base_url']}/api/plugins/telemetry/DEVICE/{self.thingsboard_config['device_id']}/values/timeseries"
            params = {
                'keys': 'timestamp',
                'limit': 1,
                'agg': 'NONE'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 401:
                logging.info('Token expired, getting new token')
                self.get_new_token()
                response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'timestamp' in data and data['timestamp']:
                    return datetime.fromisoformat(data['timestamp'][0]['value'])
            return None
        except Exception as e:
            logging.error(f"Error getting latest timestamp: {e}")
            return None

    def parse_float(self, value):
        return float(value.replace(',', '').replace(' ', ''))

    def is_alert_time(self, timestamp):
        try:
            dt = datetime.strptime(timestamp, '%d/%m/%Y %H:%M')
            now = datetime.now()
            if now.weekday() == 0:
                start_time = (now - timedelta(days=3)).replace(hour=self.night_start_hour, minute=0, second=0, microsecond=0)
            else:
                start_time = (now - timedelta(days=1)).replace(hour=self.night_start_hour, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=self.night_end_hour, minute=0, second=0, microsecond=0)
            if now.hour < self.night_end_hour:
                end_time -= timedelta(days=1)
            return start_time <= dt <= end_time
        except ValueError:
            logging.error(f"Invalid timestamp format: {timestamp}")
            return False

    def should_send_alert(self):
        now = datetime.now()
        is_weekday = now.weekday() < 5
        is_alert_hour = now.hour == self.alert_hour
        return is_weekday and is_alert_hour

    def send_consolidated_alert_email(self, exceeded_sensors):
        try:
            now = datetime.now()
            if now.weekday() == 0:
                start_date = now - timedelta(days=3)
            else:
                start_date = now - timedelta(days=1)

            date_range = f"{start_date.strftime('%Y-%m-%d')} a {now.strftime('%Y-%m-%d')}"
            
            msg = EmailMessage()
            
            if len(exceeded_sensors) == 0:
                subject = f"✅ RELATÓRIO {date_range}: Nenhum Registo Excedeu o Limite de Consumo"
                message_body = f"RELATÓRIO DE CONSUMO DE ÁGUA - {date_range}\n"
                message_body += f"Período de Análise: {start_date.strftime('%Y-%m-%d %H:%M')} até {now.strftime('%Y-%m-%d %H:%M')}\n"
                message_body += f"\nLimite Máximo por Hora: {self.max_hourly_consumption}\n"
                message_body += "NENHUM REGISTO EXCEDEU O LIMITE DE CONSUMO NO PERÍODO ANALISADO.\n"
            else:
                subject = f"⚠️ RELATÓRIO {date_range}: {len(exceeded_sensors)} Registos Excederam o Limite de Consumo"
                message_body = f"RELATÓRIO DE CONSUMO DE ÁGUA - {date_range}\n\n"
                message_body += f"Período de Análise: {start_date.strftime('%Y-%m-%d %H:%M')} até {now.strftime('%Y-%m-%d %H:%M')}\n"
                message_body += f"\nLimite Máximo por Hora: {self.max_hourly_consumption}\n\n"
                message_body += "Registos QUE EXCEDERAM O LIMITE DE CONSUMO:\n"
                
                sorted_sensors = sorted(exceeded_sensors, key=lambda x: x['sensor_id'])
                for sensor_id, group in groupby(sorted_sensors, key=lambda x: x['sensor_id']):
                    message_body += f"\nSensor ID: {sensor_id}\n"
                    message_body += "Ocorrências:\n"
                    for sensor in group:
                        message_body += f"- Timestamp: {sensor['timestamp']}\n"
                        message_body += f"  Consumo Horário: {sensor['consumo']}\n"
                        message_body += f"  Consumo Total: {sensor.get('total_consumo', 'N/A')}\n"
                        message_body += "------------------------------------------\n"
            
            msg.set_content(message_body)
            msg['Subject'] = subject
            msg['From'] = self.email_config['sender_email']
            msg['To'] = self.email_config['recipient_email']
            
            with smtplib.SMTP_SSL(self.email_config['smtp_server'], self.email_config['smtp_port']) as smtp_server:
                smtp_server.login(self.email_config['sender_email'], self.email_config['sender_password'])
                smtp_server.send_message(msg)
            
            logging.info(f"Daily alert report sent for {len(exceeded_sensors)} sensors")
        except Exception as e:
            logging.error(f"Error sending consolidated email: {e}")

    def check_consumption_alert(self, data):
        exceeded_sensors = []
        for registro in data:
            consumo_horario = registro.get('consumo', 0)
            if self.is_alert_time(registro['timestamp']) and consumo_horario > self.max_hourly_consumption:
                exceeded_sensors.append(registro)
                logging.warning(f"Consumption exceeded - Sensor: {registro['sensor_id']}, Timestamp: {registro['timestamp']}, Consumption: {consumo_horario}")
        
        if self.should_send_alert():
            self.send_consolidated_alert_email(exceeded_sensors)
        return exceeded_sensors

    def calculate_daily_consumption(self, records):
        sorted_records = sorted(records, key=lambda x: (x['sensor_id'], datetime.strptime(x['timestamp'], '%d/%m/%Y %H:%M')))
        running_totals = {}
        for record in sorted_records:
            sensor_id = record['sensor_id']
            date = datetime.strptime(record['timestamp'], '%d/%m/%Y %H:%M').strftime('%d/%m/%Y')
            key = f"{sensor_id}_{date}"
            if key not in running_totals:
                running_totals[key] = 0
            running_totals[key] += record['consumo']
            record['consumo_acumulado_dia'] = round(running_totals[key], 2)
        return sorted_records

    def send_to_thingsboard(self, sensor_data, retry_count=3):
        for attempt in range(retry_count):
            try:
                url = f"{self.thingsboard_config['base_url']}/api/v1/{self.thingsboard_config['device_token']}/telemetry"
                dt = datetime.strptime(sensor_data['timestamp'], '%d/%m/%Y %H:%M')
                telemetry_payload = {
                    "ts": int(dt.timestamp() * 1000),
                    "values": {
                        "sensor_id": sensor_data['sensor_id'],
                        "hourly_consumption": float(sensor_data['consumo']),
                        "total_consumption": float(sensor_data['total_consumo']),
                        "daily_accumulated_consumption": float(sensor_data.get('consumo_acumulado_dia', 0)),
                        "timestamp": dt.isoformat()
                    }
                }
                response = requests.post(url, json=telemetry_payload, timeout=10)
                if response.status_code == 200:
                    logging.info(f"Successfully sent data to ThingsBoard for sensor {sensor_data['sensor_id']}")
                    return True
                else:
                    logging.warning(f"Attempt {attempt + 1}/{retry_count} failed. Status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Network error on attempt {attempt + 1}/{retry_count}: {e}")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
        logging.error(f"Failed to send data to ThingsBoard after {retry_count} attempts")
        return False

    def process_new_records(self, records):
        latest_timestamp = self.get_latest_timestamp()
        if latest_timestamp is None:
            logging.warning("Could not get latest timestamp from ThingsBoard, processing all records")
            sorted_records = sorted(
                records,
                key=lambda x: datetime.strptime(x['timestamp'], '%d/%m/%Y %H:%M')
            )
        else:
            sorted_records = [
                record for record in records
                if datetime.strptime(record['timestamp'], '%d/%m/%Y %H:%M') > latest_timestamp
            ]
            sorted_records.sort(key=lambda x: datetime.strptime(x['timestamp'], '%d/%m/%Y %H:%M'))

        records_sent = 0
        for record in sorted_records:
            if self.send_to_thingsboard(record):
                records_sent += 1
            time.sleep(0.1)
        return records_sent

    def login_and_extract_table_data(self):
        os.makedirs(self.export_dir, exist_ok=True)
        attempt_count = 0
        max_attempts = 3

        while attempt_count < max_attempts:
            attempt_count += 1
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            try:
                driver.get(self.login_url)
                username_field = WebDriverWait(driver, 80).until(EC.presence_of_element_located((By.ID, "Username")))
                password_field = driver.find_element(By.ID, "Password")
                username_field.send_keys(self.username)
                password_field.send_keys(self.password)
                login_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Log in']")
                login_button.click()

                WebDriverWait(driver, 80).until(EC.url_contains("/waterlog/Sensor/Daily"))
                hourly_link = WebDriverWait(driver, 80).until(EC.presence_of_element_located((By.XPATH, "//a[@href='/waterlog/Sensor/Hourly']")))
                hourly_link.click()

                WebDriverWait(driver, 80).until(EC.url_contains("/waterlog/Sensor/Hourly"))
                length_select = WebDriverWait(driver, 80).until(EC.presence_of_element_located((By.NAME, "DataTables_Table_0_length")))
                length_options = length_select.find_elements(By.TAG_NAME, "option")
                for option in length_options:
                    if option.get_attribute("value") == "1000":
                        option.click()
                        break

                time.sleep(5)

                table_rows = driver.find_elements(By.XPATH, "//tbody/tr")
                new_records = []

                for row in table_rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        record = {
                            "sensor_id": cells[0].text,
                            "timestamp": cells[2].text,
                            "consumo": self.parse_float(cells[3].text),
                            "total_consumo": self.parse_float(cells[4].text)
                        }
                        new_records.append(record)

                new_records = self.calculate_daily_consumption(new_records)
                records_sent = self.process_new_records(new_records)
                exceeded_sensors = self.check_consumption_alert(new_records)
                
                logging.info(f"Processed {len(new_records)} records, sent {records_sent} to ThingsBoard")
                return True, exceeded_sensors

            except Exception as e:
                logging.error(f"Attempt {attempt_count} failed during data extraction: {e}")
                if attempt_count < max_attempts:
                    logging.info(f"Retrying... Attempt {attempt_count + 1}/{max_attempts}")
                    time.sleep(2 ** attempt_count)
                else:
                    logging.error("Maximum attempts reached. Failing operation.")
                    return False, []
            finally:
                driver.quit()

def main():
    login_url = "https://www.goreadycloud02.com/waterlog/Account/Login?ReturnUrl=%2Fwaterlog%2FSensor%2FDaily"
    username = "itecons@itecons.uc.pt"
    password = "Telemetria.2021"
    export_dir = r"C:\xampp\htdocs\NEWS\prodWidgets\webscrapper\AGUA"
    
    email_config = {
        'smtp_server': 'mail.uc.pt',
        'smtp_port': 465,
        'sender_email': 'itecons.noreply@itecons.uc.pt',
        'sender_password': 'Gkmb3(yehK!mn',
        'recipient_email': 'diogo.gerardo@itecons.uc.pt'
    }
    
    thingsboard_config = {
        'base_url': 'https://thingsboard.itecons.pt',
        'device_token': 'KdE4HGTLQGmrkzakv3nv',
        'device_id': '63b6fd00-c117-11ef-a0ee-df46eee9b5b2',
        'username': 'tiago.jesus@itecons.uc.pt',
        'password': 'YNKgRp9k'
    }
    
    water_log_system = WaterLogAlertSystem(
        login_url=login_url,
        username=username,
        password=password,
        export_dir=export_dir,
        max_hourly_consumption=100,
        email_config=email_config,
        thingsboard_config=thingsboard_config,
        file_retention_days=7
    )
    
    success, exceeded_sensors = water_log_system.login_and_extract_table_data()
    
    if success:
        print("Data processed and sent to ThingsBoard successfully")
        print(f"Sensors exceeding hourly limit: {len(exceeded_sensors)}")
    else:
        print("Failed to process data")

if __name__ == "__main__":
    main()
