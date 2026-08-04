# Deployment Guide - JobConnect

## Railway Deployment

### Quick Deploy
1. Push your code to GitHub
2. Connect your GitHub repository to Railway
3. Railway will automatically detect it's a Flask app
4. Set environment variables (see below)
5. Deploy

### Environment Variables for Railway
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://username:password@host:port/database
BABEL_DEFAULT_LOCALE=es
APP_NAME=JobConnect
```

### Manual Railway Setup
1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Link project: `railway link`
5. Deploy: `railway up`

### Database Setup on Railway
1. Go to Railway dashboard
2. Add a PostgreSQL service
3. Get the connection string
4. Set it in environment variables

## Manual Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
```

### Production with Gunicorn
```bash
# Install gunicorn if not already installed
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker Deployment
Create a Dockerfile:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:
```bash
docker build -t jobconnect .
docker run -p 5000:5000 jobconnect
```

### Heroku Deployment
1. Create a `Procfile`:
   ```
   web: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
   ```

2. Set environment variables in Heroku dashboard

3. Deploy:
   ```bash
   git push heroku main
   ```

## Environment Variables

| Variable | Description | Default |
|---------|-------------|---------|
| SECRET_KEY | Flask secret key | jobconnect-dev-secret-key |
| DATABASE_URL | Database connection | sqlite:///instance/jobconnect.db |
| BABEL_DEFAULT_LOCALE | Default language | es |
| APP_NAME | Application name | JobConnect |
| UPLOAD_FOLDER | Upload directory | uploads |
| MAX_CONTENT_LENGTH | Max file size | 16777216 (16MB) |
| JOBSPY_SITES | Job sites to scrape | indeed,linkedin,google,zip_recruiter |
| JOBSPY_COUNTRY | Job search country | USA |
| JOBSPY_RESULTS_WANTED | Number of results | 25 |
| CACHE_TYPE | Cache type | SimpleCache |
| RATELIMIT_DEFAULT | Rate limiting | 200 per day;50 per hour |

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Error**
   - Ensure DATABASE_URL uses `postgresql://` not `postgres://`
   - Check credentials and host

2. **Import Errors**
   - Install all dependencies: `pip install -r requirements.txt`
   - Use Python 3.10 or higher

3. **File Upload Issues**
   - Check upload folder permissions
   - Verify MAX_CONTENT_LENGTH setting

4. **Scraping Errors**
   - Check if job sites are accessible
   - Verify API keys if using premium services

### Logging
Check logs in Railway dashboard or locally:
```bash
tail -f logs/app.log
```

## Performance Optimization

### Caching
- Enable Redis for production caching
- Set appropriate cache timeouts
- Cache job search results

### Database
- Use PostgreSQL for production
- Add indexes for frequently queried fields
- Consider connection pooling

### Static Files
- Use a CDN for static assets
- Enable compression
- Set proper cache headers

## Security Considerations

1. **Secret Key**
   - Use a strong, random secret key
   - Rotate periodically

2. **File Uploads**
   - Validate file types
   - Scan for malware
   - Set size limits

3. **Rate Limiting**
   - Implement appropriate limits
   - Monitor for abuse

4. **Database Security**
   - Use strong passwords
   - Enable SSL connections
   - Regular backups

## Monitoring

### Health Check
Add a simple health check endpoint:
```python
@app.route('/health')
def health():
    return 'OK', 200
```

### Metrics
- Track job search success rate
- Monitor database performance
- Track API response times
- Monitor error rates

### Alerts
- Set up alerts for high error rates
- Monitor database connection issues
- Alert if scraping fails