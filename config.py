"""
Configuration settings for the job scraper application
"""

import os
from pathlib import Path

class Config:
    """Base configuration class"""
    
    # Basic settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    MAX_FILENAME_LENGTH = 255
    BABEL_DEFAULT_LOCALE = 'es'
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    
    # Scraping settings
    SCRAPING_TIMEOUT = 30
    SCRAPING_DELAY = (2, 5)  # Random delay between requests in seconds
    MAX_RETRIES = 3
    
    # Proxy settings
    USE_PROXY = False
    PROXY_LIST = []
    
    # Selenium settings
    SELENIUM_OPTIONS = [
        '--headless',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-notifications',
        '--disable-infobars',
        '--disable-extensions',
        '--disable-popup-blocking',
        '--disable-blink-features=AutomationControlled'
    ]
    
    # Babel settings
    LANGUAGES = {
        'en': 'English',
        'es': 'Español'
    }
    
    # Platform configurations
    PLATFORMS = {
        'weworkremotely': {
            'enabled': True,
            'base_url': 'https://weworkremotely.com',
            'search_url': 'https://weworkremotely.com/remote-jobs/search?term={}',
            'requires_selenium': False,
            'selectors': {
                'item': 'li.feature',
                'title': 'span.title',
                'company': 'span.company',
                'location': 'span.region',
                'url': 'a',
                'description': 'span.description'
            },
            'pagination': {
                'enabled': True,
                'selector': 'a.next_page',
                'max_pages': 3
            }
        },
        'remoteok': {
            'enabled': True,
            'base_url': 'https://remoteok.com',
            'search_url': 'https://remoteok.com/remote-{}-jobs',
            'requires_selenium': False,
            'selectors': {
                'item': 'tr.job',
                'title': 'td.company_and_position h2',
                'company': 'td.company_and_position h3',
                'location': 'td.location',
                'url': 'td.source a',
                'description': 'td.description'
            },
            'pagination': {
                'enabled': True,
                'selector': 'a.next_page',
                'max_pages': 3
            }
        },
        'stackoverflow': {
            'enabled': True,
            'base_url': 'https://stackoverflow.com',
            'search_url': 'https://stackoverflow.com/jobs?q={}',
            'requires_selenium': True,
            'selectors': {
                'item': 'div.-job',
                'title': 'h2.-title',
                'company': 'h3.-company',
                'location': 'span.-location',
                'url': 'a.s-link',
                'description': 'div.-description'
            },
            'pagination': {
                'enabled': True,
                'selector': 'a.s-pagination--item',
                'max_pages': 3
            }
        }
    }

    # Configuración para subida de archivos
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Configuración de caché
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Configuración de rate limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour;10 per minute"
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SECRET_KEY = 'dev'
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'America/Mexico_City'
    LANGUAGES = {
        'en': 'English',
        'es': 'Español'
    }
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    RATELIMIT_DEFAULT = "200 per day;50 per hour;10 per minute"
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    
    # Job scraping configuration
    SCRAPING_DELAY = (1, 3)  # Random delay between requests in seconds
    SCRAPING_TIMEOUT = 30  # Timeout for requests in seconds
    SELENIUM_OPTIONS = [
        '--headless',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage'
    ]
    
    # Job platforms configuration
    PLATFORMS = {
        'weworkremotely': {
            'enabled': True,
            'base_url': 'https://weworkremotely.com',
            'search_url': 'https://weworkremotely.com/remote-jobs/search?term={query}',
            'requires_selenium': False,
            'selectors': {
                'job_list': 'li.feature',
                'title': 'span.title',
                'company': 'span.company',
                'location': 'span.region',
                'description': 'span.description',
                'url': 'a',
                'posted_date': 'time',
                'tags': 'span.tags'
            },
            'pagination': {
                'enabled': True,
                'max_pages': 3,
                'selector': 'a.next_page'
            }
        },
        'remoteok': {
            'enabled': True,
            'base_url': 'https://remoteok.com',
            'search_url': 'https://remoteok.com/remote-{query}-jobs',
            'requires_selenium': False,
            'selectors': {
                'job_list': 'tr.job',
                'title': 'td.company_and_position h2',
                'company': 'td.company_and_position h3',
                'location': 'td.location',
                'description': 'td.description',
                'url': 'td.source a',
                'posted_date': 'td.time',
                'tags': 'td.tags span'
            },
            'pagination': {
                'enabled': True,
                'max_pages': 3,
                'selector': 'a.next_page'
            }
        },
        'stackoverflow': {
            'enabled': True,
            'base_url': 'https://stackoverflow.com',
            'search_url': 'https://stackoverflow.com/jobs?q={query}&l=remote',
            'requires_selenium': True,
            'selectors': {
                'job_list': 'div.-job',
                'title': 'h2.-title',
                'company': 'h3.-company',
                'location': 'span.-location',
                'description': 'div.-description',
                'url': 'a.-title',
                'posted_date': 'span.fc-black-500',
                'tags': 'div.-tags span'
            },
            'pagination': {
                'enabled': True,
                'max_pages': 3,
                'selector': 'a.s-pagination--item'
            }
        }
    }

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production-specific settings
    USE_PROXY = True
    PROXY_LIST = [
        # Add your proxy list here
    ]

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    
    # Testing-specific settings
    SCRAPING_DELAY = (0, 1)  # Faster for testing
    MAX_RETRIES = 1

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 