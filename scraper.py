"""
Job scraper module for finding job opportunities based on CV text
"""

import os
import re
import json
import logging
import hashlib
import time
import random
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse, quote_plus
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from fake_useragent import UserAgent
import backoff
import cloudscraper
from collections import Counter

logger = logging.getLogger(__name__)

class JobScraper:
    """Class for scraping job listings from various platforms"""
    
    def __init__(self, app):
        """
        Initialize the job scraper with configuration settings
        
        Args:
            app: The application object
        """
        # Ensure the latest scraper code is loaded
        self.app = app
        self.config = app.config
        self.session = requests.Session()
        self.ua = UserAgent()
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration"""
        logger = logging.getLogger('JobScraper')
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join('static', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(os.path.join(log_dir, 'scraper.log'))
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _get_random_delay(self) -> float:
        """Get a random delay between requests"""
        return random.uniform(*self.config['SCRAPING_DELAY'])
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for HTTP requests"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        }
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format and security"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception:
            return False
    
    def _generate_job_id(self, title: str, company: str) -> str:
        """Generate a unique job ID"""
        job_str = f"{title}{company}{time.time()}"
        return hashlib.md5(job_str.encode()).hexdigest()
    
    @backoff.on_exception(backoff.expo, 
                         (requests.exceptions.RequestException, TimeoutException),
                         max_tries=3)
    def _make_request(self, url: str, use_selenium: bool = False) -> Optional[str]:
        """
        Realiza una solicitud HTTP a una URL.
        
        Args:
            url (str): URL a solicitar
            use_selenium (bool): Si se debe usar Selenium
            
        Returns:
            Optional[str]: Contenido de la respuesta o None si hay error
        """
        try:
            # Validar URL
            if not self._validate_url(url):
                self.logger.error(f"Invalid URL: {url}")
                return None
            
            # Agregar delay aleatorio
            time.sleep(self._get_random_delay())
            
            if use_selenium:
                # Configurar opciones de Chrome
                chrome_options = webdriver.ChromeOptions()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument(f'user-agent={self.ua.random}')
                
                # Inicializar driver
                driver = webdriver.Chrome(options=chrome_options)
                try:
                    driver.get(url)
                    time.sleep(2)  # Esperar a que cargue
                    return driver.page_source
                finally:
                    driver.quit()
            else:
                # Usar cloudscraper para evadir detección de bots
                scraper = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False
                    }
                )
                
                # Realizar solicitud
                response = scraper.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30
                )
                
                # Verificar respuesta
                if response.status_code == 200:
                    return response.text
                else:
                    self.logger.error(f"Error {response.status_code} for {url}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error making request to {url}: {str(e)}")
            return None
    
    def _extract_job_data(self, element: BeautifulSoup, platform: str) -> Optional[Dict]:
        """
        Extrae la información de un trabajo desde un elemento HTML.
        
        Args:
            element (BeautifulSoup): Elemento HTML que contiene la información del trabajo
            platform (str): Nombre de la plataforma
            
        Returns:
            Optional[Dict]: Diccionario con la información del trabajo o None si hay error
        """
        try:
            platform_config = self.config['PLATFORMS'][platform]
            selectors = platform_config['selectors']
            
            # Extraer datos básicos
            title = element.select_one(selectors['title'])
            title = title.get_text().strip() if title else None
            
            company = element.select_one(selectors['company'])
            company = company.get_text().strip() if company else None
            
            location = element.select_one(selectors['location'])
            location = location.get_text().strip() if location else None
            
            description = element.select_one(selectors['description'])
            description = description.get_text().strip() if description else None
            
            url = element.select_one(selectors['url'])
            url = url.get('href') if url else None
            
            # Validar datos requeridos
            if not all([title, company, url]):
                return None
                
            # Construir URL completa si es relativa
            if url and not url.startswith(('http://', 'https://')):
                url = urljoin(platform_config['base_url'], url)
            
            # Generar ID único
            job_id = self._generate_job_id(title, company)
            
            # Construir diccionario de trabajo
            job_data = {
                'id': job_id,
                'title': title,
                'company': company,
                'location': location or 'Remote',
                'description': description or '',
                'url': url,
                'platform': platform,
                'posted_date': None,  # Opcional
                'salary': None,  # Opcional
                'tags': []  # Opcional
            }
            
            # Extraer datos opcionales si están disponibles
            if 'posted_date' in selectors:
                date_elem = element.select_one(selectors['posted_date'])
                if date_elem:
                    job_data['posted_date'] = date_elem.get_text().strip()
                
            if 'salary' in selectors:
                salary_elem = element.select_one(selectors['salary'])
                if salary_elem:
                    job_data['salary'] = salary_elem.get_text().strip()
                
            if 'tags' in selectors:
                tag_elems = element.select(selectors['tags'])
                job_data['tags'] = [tag.get_text().strip() for tag in tag_elems]
            
            return job_data
            
        except Exception as e:
            self.logger.error(f"Error extracting job data: {str(e)}")
            return None
    
    def _scrape_platform(self, platform: str, keywords: List[str]) -> List[Dict]:
        """Scrape jobs from a specific platform"""
        if not platform in self.config['PLATFORMS']:
            self.logger.error(f"Invalid platform: {platform}")
            return []
            
        # Usar solo las dos primeras palabras clave para la búsqueda
        search_terms = '+'.join(keywords[:2])
        
        # Construir URL de búsqueda
        if platform == 'stackoverflow':
            url = f"https://stackoverflow.com/jobs?q={search_terms}&l=remote"
        elif platform == 'weworkremotely':
            url = f"https://weworkremotely.com/remote-jobs/search?term={search_terms}"
        elif platform == 'remoteok':
            url = f"https://remoteok.com/remote-{search_terms}-jobs"
        else:
            self.logger.error(f"Unsupported platform: {platform}")
            return []
            
        self.logger.info(f"Scraping {platform} with URL: {url}")
        
        try:
            # Usar Selenium para evitar bloqueos
            html_content = self._make_request(url, use_selenium=True)
            if not html_content:
                return []
                
            soup = BeautifulSoup(html_content, 'html.parser')
            jobs = []
            
            # Extraer trabajos según la plataforma
            if platform == 'stackoverflow':
                job_elements = soup.select('.job-result-card')
                for job in job_elements:
                    title = job.select_one('.job-result-card__title')
                    company = job.select_one('.job-result-card__company-name')
                    location = job.select_one('.job-result-card__location')
                    if title and company:
                        jobs.append({
                            'title': title.text.strip(),
                            'company': company.text.strip(),
                            'location': location.text.strip() if location else 'Remote',
                            'url': f"https://stackoverflow.com{title.get('href', '')}",
                            'platform': platform
                        })
                        
            elif platform == 'weworkremotely':
                job_elements = soup.select('.job-card')
                for job in job_elements:
                    title = job.select_one('.job-card__title')
                    company = job.select_one('.job-card__company')
                    if title and company:
                        jobs.append({
                            'title': title.text.strip(),
                            'company': company.text.strip(),
                            'location': 'Remote',
                            'url': f"https://weworkremotely.com{title.get('href', '')}",
                            'platform': platform
                        })
                        
            elif platform == 'remoteok':
                job_elements = soup.select('.job')
                for job in job_elements:
                    title = job.select_one('.company_and_position h2')
                    company = job.select_one('.company_and_position h3')
                    if title and company:
                        jobs.append({
                            'title': title.text.strip(),
                            'company': company.text.strip(),
                            'location': 'Remote',
                            'url': f"https://remoteok.com{title.get('href', '')}",
                            'platform': platform
                        })
                        
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error scraping {platform}: {str(e)}")
            return []
    
    def get_jobs(self, cv_text: str, language: str = 'en') -> List[Dict]:
        """Search for jobs using CV text"""
        self.logger.info("Starting job search")
        
        # Validar y limpiar el texto del CV
        if not isinstance(cv_text, str):
            self.logger.error(f"Invalid CV text type: {type(cv_text)}")
            return []
            
        cv_text = cv_text.strip()
        if not cv_text:
            self.logger.error("Empty CV text")
            return []
            
        # Extraer palabras clave
        keywords = self._extract_keywords(cv_text)
        if not keywords:
            self.logger.warning("No keywords found in CV")
            return []
            
        self.logger.info(f"Using keywords: {keywords}")
        
        # Buscar trabajos en cada plataforma
        all_jobs = []
        seen_jobs = set()
        
        for platform in self.config['PLATFORMS']:
            try:
                platform_jobs = self._scrape_platform(platform, keywords)
                for job in platform_jobs:
                    job_id = self._generate_job_id(job['title'], job['company'])
                    if job_id not in seen_jobs:
                        seen_jobs.add(job_id)
                        all_jobs.append(job)
            except Exception as e:
                self.logger.error(f"Error scraping {platform}: {str(e)}")
                continue
                
        self.logger.info(f"Found {len(all_jobs)} unique jobs")
        return all_jobs

    def _extract_keywords(self, cv_text: str) -> List[str]:
        """Extract relevant keywords from CV text"""
        try:
            # Ensure cv_text is a string
            if isinstance(cv_text, list):
                cv_text = ' '.join(cv_text)
            elif not isinstance(cv_text, str):
                self.logger.error(f"Invalid CV text type: {type(cv_text)}")
                return []

            # Clean and process text
            cv_text = cv_text.strip().lower()
            if not cv_text:
                self.logger.error("Empty CV text after cleaning")
                return []

            # Lista de palabras clave técnicas comunes
            technical_keywords = {
                'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node', 'express',
                'django', 'flask', 'spring', 'hibernate', 'sql', 'mysql', 'postgresql', 'mongodb',
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'ci/cd',
                'agile', 'scrum', 'jira', 'confluence', 'rest', 'graphql', 'api', 'microservices',
                'data', 'ai', 'ml', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn',
                'testing', 'selenium', 'junit', 'pytest', 'cypress', 'devops', 'linux', 'bash',
                'typescript', 'php', 'ruby', 'rails', 'go', 'rust', 'c++', 'c#', '.net',
                'html', 'css', 'sass', 'less', 'webpack', 'babel', 'npm', 'yarn',
                'redis', 'kafka', 'rabbitmq', 'elasticsearch', 'solr', 'hadoop', 'spark',
                'security', 'oauth', 'jwt', 'ssl', 'tls', 'encryption', 'authentication',
                'blockchain', 'ethereum', 'solidity', 'web3', 'cryptocurrency', 'fintech',
                'mobile', 'ios', 'android', 'react native', 'flutter', 'swift', 'kotlin'
            } # Asegúrate de que esta llave de cierre esté presente

            # Convert text to words and find technical keywords
            words = cv_text.split()
            found_keywords = [word for word in words if word in technical_keywords]

            # If no technical keywords found, use most common words (excluding stop words and short words)
            if not found_keywords:
                stop_words = set([
                    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
                    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
                    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
                    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
                    'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
                    'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
                    'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
                    'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
                    'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
                    'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
                ])

                word_freq = {}
                for word in words:
                    if word not in stop_words and len(word) > 2:
                        word_freq[word] = word_freq.get(word, 0) + 1

                found_keywords = [word for word, _ in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]]

            # Log and return up to 3 keywords
            self.logger.info(f"Extracted keywords: {found_keywords[:3]}")
            return found_keywords[:3]

        except Exception as e:
            self.logger.error(f"Error extracting keywords: {str(e)}")
            return []