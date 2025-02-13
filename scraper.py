import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import logging
from urllib.parse import quote_plus, urljoin

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurar Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")  # Ejecutar en segundo plano
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

def get_selenium_driver():
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

# Configuración de User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/119.0.0.0"
]

def get_random_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

# Plataformas de empleo (con selectores corregidos)
PLATFORM_CONFIG = {
    'weworkremotely': {
        'url': 'https://weworkremotely.com/remote-jobs/search?term={keyword}',
        'selectors': {
            'item': 'li.feature',
            'title': 'span.title',
            'company': 'span.company',
            'location': 'span.region',
            'url': 'a'
        },
        'selenium': False
    },
    'remoteok': {
        'url': 'https://remoteok.io/remote-{keyword}-jobs',
        'selectors': {
            'item': 'tr.job',
            'title': 'td.company h2',  # Selector corregido
            'company': 'td.company h3',
            'location': 'div.location',
            'url': 'a'
        },
        'selenium': True
    }
}

def get_jobs(cv_text, lang='es'):
    keywords = extract_keywords(cv_text, lang)
    jobs = []
    
    for platform, config in PLATFORM_CONFIG.items():
        try:
            time.sleep(random.uniform(1, 3))  # Pausa aleatoria para evitar bloqueos
            platform_jobs = scrape_platform(platform, config, keywords)
            jobs.extend(platform_jobs)
        except Exception as e:
            logging.error(f"Error en {platform}: {str(e)}")

    return jobs

def scrape_platform(platform_name, config, keywords):
    search_url = config['url'].format(keyword=quote_plus(' '.join(keywords)))
    logging.info(f"Buscando en {platform_name}: {search_url}")
    
    if config.get('selenium', False):
        return scrape_with_selenium(search_url, config)
    else:
        return scrape_with_requests(search_url, config)

def scrape_with_requests(url, config):
    headers = get_random_headers()
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Guardamos el HTML para revisión manual
    domain = url.split("//")[1].split("/")[0]
    with open(f"debug_{domain}.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    return parse_jobs(soup, config)

def scrape_with_selenium(url, config):
    driver = get_selenium_driver()
    driver.get(url)
    time.sleep(5)  # Esperar a que cargue el contenido dinámico
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # Guardamos el HTML para revisión manual
    domain = url.split("//")[1].split("/")[0]
    with open(f"debug_{domain}.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    return parse_jobs(soup, config)

def parse_jobs(soup, config):
    jobs = []
    for item in soup.select(config['selectors']['item']):
        print(f"Elemento HTML:\n{item.prettify()}")  # Debug: Ver el contenido de cada oferta
        try:
            title = item.select_one(config['selectors']['title'])
            company = item.select_one(config['selectors']['company'])
            location = item.select_one(config['selectors']['location'])
            url = item.select_one(config['selectors']['url'])

            title_text = title.get_text(strip=True) if title else 'NO ENCONTRADO'
            company_text = company.get_text(strip=True) if company else 'N/A'
            location_text = location.get_text(strip=True) if location else 'Remote'
            url_text = urljoin(config['url'], url['href']) if url and 'href' in url.attrs else 'N/A'

            print(f"Título: {title_text}, Empresa: {company_text}, Ubicación: {location_text}, URL: {url_text}")  # Debug

            jobs.append({
                'title': title_text,
                'company': company_text,
                'location': location_text,
                'url': url_text,
                'platform': config
            })
        except Exception as e:
            logging.error(f"Error al procesar un elemento: {str(e)}")
    return jobs

def extract_keywords(text, lang):
    keyword_dict = {
        'en': ['python', 'java', 'developer', 'engineer', 'remote', 'logistics', 'marketing'],
        'es': ['python', 'java', 'desarrollador', 'ingeniero', 'remoto', 'logística', 'marketing']
    }
    words = text.lower().split()
    return [word for word in words if word in keyword_dict.get(lang, [])]
