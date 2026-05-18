"""
Configuration settings for the JobConnect application.

Uses environment variables for sensitive settings with sensible defaults
for development. Production should always use environment variables.
"""

import os
from pathlib import Path
from datetime import timedelta

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration class with shared settings."""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'jobconnect-dev-secret-key-change-in-production-2024')
    WTF_CSRF_ENABLED = True

    # Application
    APP_NAME = os.environ.get('APP_NAME', 'JobConnect')
    MAX_FILENAME_LENGTH = 255

    # Database - fix Railway's postgres:// to postgresql:// for SQLAlchemy 2.x
    @staticmethod
    def _get_database_url():
        url = os.environ.get('DATABASE_URL', '')
        if url:
            # Railway/Heroku use postgres:// but SQLAlchemy 2.x needs postgresql://
            if url.startswith('postgres://'):
                url = url.replace('postgres://', 'postgresql://', 1)
            return url
        return f'sqlite:///{BASE_DIR / "instance" / "jobconnect.db"}'

    SQLALCHEMY_DATABASE_URI = None  # Set in init_app
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Internationalization
    BABEL_DEFAULT_LOCALE = os.environ.get('BABEL_DEFAULT_LOCALE', 'es')
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    LANGUAGES = {
        'en': 'English',
        'es': 'Español',
        'it': 'Italiano'
    }

    # File uploads
    UPLOAD_FOLDER = os.environ.get(
        'UPLOAD_FOLDER', str(BASE_DIR / 'uploads')
    )
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}

    # Scraping settings
    SCRAPING_TIMEOUT = int(os.environ.get('SCRAPING_TIMEOUT', 30))
    SCRAPING_DELAY = (2, 5)  # Random delay range in seconds
    MAX_RETRIES = 3
    MAX_JOBS_PER_PLATFORM = 20

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

    # Cache settings
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))

    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour;10 per minute"
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_STRATEGY = "fixed-window"

    # Logging
    LOG_DIR = str(BASE_DIR / 'static' / 'logs')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Platform configurations for job scraping
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
    }

    @staticmethod
    def init_app(app):
        """Initialize application-specific settings."""
        # Set database URL with postgres:// fix
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            app.config['SQLALCHEMY_DATABASE_URI'] = Config._get_database_url()
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
        os.makedirs(app.config.get('LOG_DIR', 'static/logs'), exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    SCRAPING_DELAY = (1, 3)
    SESSION_COOKIE_SECURE = False

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        import logging
        app.logger.setLevel(logging.DEBUG)


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    USE_PROXY = True

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        import logging
        app.logger.setLevel(logging.WARNING)


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SCRAPING_DELAY = (0, 0.5)
    MAX_RETRIES = 1
    WTF_CSRF_ENABLED = False

    @staticmethod
    def init_app(app):
        Config.init_app(app)


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
