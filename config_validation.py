"""
Configuration validation module for JobConnect application.
Validates configuration files and environment variables.
"""

import os
import re
from pathlib import Path
from config_loader import validate_config, get_config_value

def validate_email_config():
    """
    Validate email configuration settings.
    
    Returns:
        dict: Validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    mail_config = {
        'server': get_config_value('MAIL_SERVER'),
        'port': get_config_value('MAIL_PORT'),
        'use_tls': get_config_value('MAIL_USE_TLS'),
        'username': get_config_value('MAIL_USERNAME'),
        'password': get_config_value('MAIL_PASSWORD')
    }
    
    # Check if email configuration appears to be complete
    if mail_config['username'] and mail_config['password']:
        if not mail_config['server'] or mail_config['server'] == 'smtp.gmail.com':
            results['warnings'].append("Email server configuration appears to use default values")
        
        # Validate port number
        try:
            port = int(mail_config['port'])
            if port < 1 or port > 65535:
                results['errors'].append("Invalid email port number")
                results['valid'] = False
        except (ValueError, TypeError):
            results['errors'].append("Email port must be a number")
            results['valid'] = False
    
    return results

def validate_database_config():
    """
    Validate database configuration settings.
    
    Returns:
        dict: Validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    db_url = get_config_value('DATABASE_URL')
    
    if not db_url:
        results['errors'].append("Database URL is required")
        results['valid'] = False
        return results
    
    # Check for common database formats
    if db_url.startswith('sqlite://'):
        # SQLite validation
        if 'memory:' not in db_url:
            db_path = db_url.replace('sqlite://', '')
            if not Path(db_path).parent.exists():
                results['warnings'].append("SQLite database directory does not exist")
    
    elif db_url.startswith('postgresql://') or db_url.startswith('postgres://'):
        # PostgreSQL validation
        if '@' not in db_url or '/' not in db_url:
            results['errors'].append("PostgreSQL URL format appears incorrect")
            results['valid'] = False
        
        # Check for postgres:// and warn about needing postgresql://
        if db_url.startswith('postgres://'):
            results['warnings'].append("Using 'postgres://' prefix - should use 'postgresql://' for SQLAlchemy 2.x")
    
    else:
        results['warnings'].append("Unsupported database type detected")
    
    return results

def validate_api_keys():
    """
    Validate API key configuration.
    
    Returns:
        dict: Validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    api_keys = {
        'indeed': get_config_value('INDEED_API_KEY'),
        'linkedin_client_id': get_config_value('LINKEDIN_CLIENT_ID'),
        'linkedin_client_secret': get_config_value('LINKEDIN_CLIENT_SECRET'),
        'google_jobs': get_config_value('GOOGLE_JOBS_API_KEY')
    }
    
    # Check for placeholder values
    for key, value in api_keys.items():
        if value and value.startswith('your-'):
            results['warnings'].append(f"API key '{key}' appears to be using a placeholder value")
        
        # Simple API key format validation
        if value and not re.match(r'^[a-zA-Z0-9\-_\.]+$', value):
            results['warnings'].append(f"API key '{key}' contains unusual characters")
    
    return results

def validate_file_upload_config():
    """
    Validate file upload configuration.
    
    Returns:
        dict: Validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    upload_folder = get_config_value('UPLOAD_FOLDER', 'uploads')
    max_content_length = get_config_value('MAX_CONTENT_LENGTH', '16777216')  # 16MB in bytes
    
    # Validate max content length
    try:
        length = int(max_content_length)
        if length < 1024 or length > 100 * 1024 * 1024:  # Between 1KB and 100MB
            results['warnings'].append("Max content length is outside typical range (1KB-100MB)")
    except (ValueError, TypeError):
        results['errors'].append("Max content length must be a number")
        results['valid'] = False
    
    # Check if upload directory exists
    upload_path = Path(upload_folder)
    if not upload_path.exists():
        try:
            upload_path.mkdir(parents=True, exist_ok=True)
            results['warnings'].append(f"Created upload directory: {upload_folder}")
        except Exception as e:
            results['errors'].append(f"Cannot create upload directory: {str(e)}")
            results['valid'] = False
    
    return results

def run_all_validations():
    """
    Run all configuration validations.
    
    Returns:
        dict: Combined validation results
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'details': {}
    }
    
    # Run individual validations
    validations = [
        ('basic', validate_config),
        ('email', validate_email_config),
        ('database', validate_database_config),
        ('api_keys', validate_api_keys),
        ('file_uploads', validate_file_upload_config)
    ]
    
    for name, validation_func in validations:
        validation_result = validation_func()
        results['details'][name] = validation_result
        
        # Aggregate errors and warnings
        if not validation_result['valid']:
            results['valid'] = False
        
        results['errors'].extend([f"{name}: {error}" for error in validation_result['errors']])
        results['warnings'].extend([f"{name}: {warning}" for warning in validation_result['warnings']])
    
    return results

def print_validation_summary(results):
    """
    Print a summary of validation results.
    
    Args:
        results (dict): Validation results from run_all_validations
    """
    print("=== Configuration Validation Summary ===")
    print(f"Overall Status: {'✅ VALID' if results['valid'] else '❌ INVALID'}")
    print()
    
    if results['errors']:
        print("❌ Errors:")
        for error in results['errors']:
            print(f"  - {error}")
        print()
    
    if results['warnings']:
        print("⚠️  Warnings:")
        for warning in results['warnings']:
            print(f"  - {warning}")
        print()
    
    if results['valid'] and not results['errors'] and not results['warnings']:
        print("✅ Configuration is valid with no issues!")

if __name__ == "__main__":
    # Run validation when script is executed directly
    validation_results = run_all_validations()
    print_validation_summary(validation_results)