"""
Configuration loader for the JobConnect application.
Handles configuration loading and validation.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_config_value(key, default=None, required=False):
    """
    Get a configuration value from environment variables.
    
    Args:
        key (str): The configuration key to look up
        default (any, optional): Default value if not found
        required (bool): Whether this value is required
        
    Returns:
        The configuration value or default
        
    Raises:
        ValueError: If required is True and value is not found
    """
    value = os.environ.get(key, default)
    
    if required and not value:
        raise ValueError(f"Required configuration '{key}' is missing or empty")
    
    return value

def validate_config():
    """
    Validate all required configuration values.
    
    Returns:
        dict: Dictionary of validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Check required values
    required_keys = [
        'SECRET_KEY',
        'DATABASE_URL'
    ]
    
    for key in required_keys:
        value = os.environ.get(key)
        if not value or value == f'your-{key.lower().replace("_", "-")}':
            results['errors'].append(f"Missing or default value for required key: {key}")
            results['valid'] = False
    
    # Check API keys if present
    api_keys = [
        'INDEED_API_KEY',
        'LINKEDIN_CLIENT_ID',
        'LINKEDIN_CLIENT_SECRET',
        'GOOGLE_JOBS_API_KEY'
    ]
    
    for key in api_keys:
        value = os.environ.get(key)
        if value and value.startswith('your-'):
            results['warnings'].append(f"API key '{key}' appears to be using a default value")
    
    return results

def get_database_url():
    """
    Get the database URL with proper formatting.
    
    Returns:
        str: The formatted database URL
    """
    url = get_config_value('DATABASE_URL')
    
    # Fix postgres:// to postgresql:// for SQLAlchemy 2.x
    if url and url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    
    return url

def setup_logging(log_level=None):
    """
    Setup logging configuration.
    
    Args:
        log_level (str, optional): Log level to use
    """
    log_level = log_level or get_config_value('LOG_LEVEL', 'INFO')
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

def get_upload_folder():
    """
    Get the upload folder path.
    
    Returns:
        str: Path to upload folder
    """
    upload_folder = get_config_value('UPLOAD_FOLDER', 'uploads')
    return Path(upload_folder).resolve()

# Convenience functions for common configuration values
def get_secret_key():
    """Get the secret key."""
    return get_config_value('SECRET_KEY', required=True)

def get_database_uri():
    """Get the database URI."""
    return get_database_url()

def get_mail_config():
    """Get mail configuration as a dictionary."""
    return {
        'server': get_config_value('MAIL_SERVER', 'smtp.gmail.com'),
        'port': int(get_config_value('MAIL_PORT', 587)),
        'use_tls': get_config_value('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1'],
        'username': get_config_value('MAIL_USERNAME', ''),
        'password': get_config_value('MAIL_PASSWORD', ''),
        'default_sender': get_config_value('MAIL_DEFAULT_SENDER', 'noreply@jobconnect.com')
    }

def get_jobspy_config():
    """Get JobSpy configuration as a dictionary."""
    return {
        'sites': ['indeed', 'linkedin', 'google', 'zip_recruiter'],
        'country': get_config_value('JOBSPY_COUNTRY', 'USA'),
        'results_wanted': int(get_config_value('JOBSPY_RESULTS_WANTED', 25)),
        'hours_old': int(get_config_value('JOBSPY_HOURS_OLD', 168))
    }

def get_api_keys():
    """Get API keys as a dictionary."""
    return {
        'indeed': get_config_value('INDEED_API_KEY', ''),
        'linkedin_client_id': get_config_value('LINKEDIN_CLIENT_ID', ''),
        'linkedin_client_secret': get_config_value('LINKEDIN_CLIENT_SECRET', ''),
        'google_jobs': get_config_value('GOOGLE_JOBS_API_KEY', '')
    }