# Configuration Guide for JobConnect

This document explains the configuration options for the JobConnect application.

## Environment Variables

### Required Variables

- `SECRET_KEY`: Flask secret key for session security
- `DATABASE_URL`: Database connection URL

### Optional Variables

#### Application Settings
- `FLASK_ENV`: Environment (development/production/testing)
- `APP_NAME`: Application name (default: JobConnect)
- `BABEL_DEFAULT_LOCALE`: Default language (default: es)
- `LOG_LEVEL`: Logging level (default: INFO)

#### Database Settings
- `DATABASE_URL`: Database connection URL
- `SQLALCHEMY_TRACK_MODIFICATIONS`: Track modifications (default: false)

#### Email Configuration
- `MAIL_SERVER`: SMTP server (default: smtp.gmail.com)
- `MAIL_PORT`: SMTP port (default: 587)
- `MAIL_USE_TLS`: Use TLS (default: true)
- `MAIL_USERNAME`: Email username
- `MAIL_PASSWORD`: Email password
- `MAIL_DEFAULT_SENDER`: Default sender email

#### File Uploads
- `UPLOAD_FOLDER`: Upload directory (default: uploads)
- `MAX_CONTENT_LENGTH`: Maximum file size (default: 16MB)

#### JobSpy Settings
- `JOBSPY_COUNTRY`: Country code (default: USA)
- `JOBSPY_RESULTS_WANTED`: Number of results (default: 25)
- `JOBSPY_HOURS_OLD`: Hours old (default: 168)

#### API Keys
- `INDEED_API_KEY`: Indeed API key
- `LINKEDIN_CLIENT_ID`: LinkedIn client ID
- `LINKEDIN_CLIENT_SECRET`: LinkedIn client secret
- `GOOGLE_JOBS_API_KEY`: Google Jobs API key

#### Scraping Settings
- `SCRAPING_TIMEOUT`: Timeout in seconds (default: 30)
- `MAX_RETRIES`: Maximum retries (default: 3)

#### Cache Settings
- `CACHE_TYPE`: Cache type (default: SimpleCache)
- `CACHE_DEFAULT_TIMEOUT`: Cache timeout in seconds (default: 300)

#### Rate Limiting
- `RATELIMIT_STORAGE_URL`: Rate limit storage URL (default: memory://)
- `RATELIMIT_DEFAULT`: Default rate limit (default: 200 per day;50 per hour;10 per minute)
- `RATELIMIT_STRATEGY`: Rate limit strategy (default: fixed-window)

## Configuration Files

### config.py
Main configuration class with all settings defined.

### config_loader.py
Utility functions for loading and validating configuration.

### config_validation.py
Validation functions for configuration settings.

### config_example.json
Example configuration in JSON format.

### .env.example
Example environment variables file.

## Database Configuration

### PostgreSQL
For production, use PostgreSQL:

```
DATABASE_URL=postgresql://user:password@host:5432/jobconnect
```

### SQLite
For development, SQLite is used by default:

```
DATABASE_URL=sqlite:///instance/jobconnect.db
```

## Email Configuration

### Gmail Configuration
For Gmail, use:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

Note: Use an app-specific password for Gmail.

## API Keys

### Indeed API
Get API key from Indeed Developer Portal.

### LinkedIn API
Get client ID and secret from LinkedIn Developer Portal.

### Google Jobs API
Get API key from Google Cloud Console.

## Validation

Run configuration validation:

```bash
python config_validation.py
```

This will check all configuration settings and report any issues.

## Security Considerations

1. Never commit real API keys or secrets to version control
2. Use environment variables for sensitive information
3. Change default secret keys in production
4. Use HTTPS in production
5. Set proper file permissions for upload directory

## Deployment

For deployment, ensure:

1. All required environment variables are set
2. Database is properly configured
3. Upload directory exists and has proper permissions
4. SSL/TLS is configured for production
5. Rate limiting is appropriate for your usage

## Troubleshooting

Common issues and solutions:

### Database Connection Issues
- Check DATABASE_URL format
- Ensure database server is accessible
- Verify credentials

### Email Issues
- Verify SMTP settings
- Check firewall rules
- Use app-specific passwords for Gmail

### File Upload Issues
- Check upload directory permissions
- Verify MAX_CONTENT_LENGTH setting
- Check disk space