import requests
from bs4 import BeautifulSoup
import logging
import time
from random import choice
from urllib.parse import urljoin, quote_plus

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# User-Agents para evitar bloqueos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/119.0.0.0"
]

def get_random_headers():
    return {"User-Agent": choice(USER_AGENTS)}

# Plataformas de scraping
PLATFORM_CONFIG = {
    'weworkremotely': {
        'url': 'https://weworkremotely.com/remote-jobs/search?term=',
        'selectors': {
            'item': 'section.jobs li.feature',
            'title': 'span.title',
            'company': 'span.company',
            'location': 'span.region',
            'url': 'a'
        }
    },
    'remoteok': {
        'url': 'https://remoteok.io/remote-{keyword}-jobs',
        'selectors': {
            'item': 'tr.job',
            'title': 'h2',
            'company': 'h3.company',
            'location': 'div.location',
            'url': 'a'
        }
    }
}

def get_jobs(cv_text="", lang='es'):
    keywords = extract_keywords(cv_text, lang)
    jobs = []

    for platform, config in PLATFORM_CONFIG.items():
        try:
            time.sleep(1)
            platform_jobs = scrape_platform(platform, config, keywords, lang)
            jobs.extend(platform_jobs)
        except Exception as e:
            logging.error(f"Error en {platform}: {str(e)}")

    return sorted(jobs, key=lambda x: len(x['keywords_matched']), reverse=True)[:50]

def scrape_platform(platform_name, config, keywords, lang):
    search_url = config['url'].format(keyword=quote_plus(' '.join(keywords)))
    headers = get_random_headers()
    headers["Accept-Language"] = "es-ES,es;q=0.9" if lang == 'es' else "en-US,en;q=0.9"

    logging.info(f"Buscando en {platform_name}: {search_url}")
    
    try:
        response = requests.get(search_url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al obtener datos de {platform_name}: {str(e)}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    platform_jobs = []
    
    for item in soup.select(config['selectors']['item']):
        try:
            title_element = item.select_one(config['selectors']['title'])
            company_element = item.select_one(config['selectors']['company'])
            location_element = item.select_one(config['selectors']['location'])
            url_element = item.select_one(config['selectors']['url'])
            
            title = title_element.get_text(strip=True) if title_element else 'N/A'
            company = company_element.get_text(strip=True) if company_element else 'N/A'
            location = location_element.get_text(strip=True) if location_element else 'Remote'
            url = urljoin(search_url, url_element['href']) if url_element and url_element.has_attr('href') else '#'

            keywords_matched = [kw for kw in keywords if kw.lower() in item.text.lower()]

            if title != 'N/A':
                platform_jobs.append({
                    'title': title,
                    'company': company,
                    'location': location,
                    'url': url,
                    'platform': platform_name,
                    'keywords_matched': keywords_matched
                })
            else:
                logging.warning(f"Trabajo sin título en {platform_name}, descartado")

        except Exception as e:
            logging.error(f"Error al procesar un elemento en {platform_name}: {str(e)}")

    return platform_jobs

def extract_keywords(text, lang):
    keyword_dict = {
        'en': ['python', 'java', 'developer', 'engineer', 'remote', 'logistics', 'marketing', 'teacher', 'doctor'],
        'es': ['python', 'java', 'desarrollador', 'ingeniero', 'remoto', 'logística', 'marketing', 'profesor', 'médico']
    }

    words = text.lower().split()
    return [word for word in words if word in keyword_dict.get(lang, [])]
