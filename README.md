# Job Finder Application

A Flask-based web application that helps users find job opportunities by analyzing their CV and matching it with job listings from various remote job platforms.

## Features

- CV parsing and analysis
- Job scraping from multiple platforms (WeWorkRemotely, RemoteOK)
- AI-powered job matching
- Multi-language support (English, Spanish, Italian)
- Rate limiting and caching
- Secure file handling
- Responsive web interface

## Prerequisites

- Python 3.8 or higher
- Chrome browser (for Selenium)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Job_finder_app
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

The application can be configured through environment variables or the config.py file. Key settings include:

- `SECRET_KEY`: Flask secret key
- `UPLOAD_FOLDER`: Directory for temporary file uploads
- `BABEL_DEFAULT_LOCALE`: Default language
- `CACHE_TYPE`: Cache backend type
- `RATELIMIT_DEFAULT`: Rate limiting rules

## Usage

1. Start the development server:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Upload your CV (PDF or DOCX format)

4. View matched job opportunities

## Development

### Running Tests
```bash
pytest
```

### Code Style
```bash
black .
flake8
mypy .
```

## Project Structure

```
Job_finder_app/
├── app.py              # Main application file
├── config.py           # Configuration settings
├── scraper.py          # Job scraping module
├── cv_parser.py        # CV parsing module
├── ai_matcher.py       # Job matching module
├── requirements.txt    # Project dependencies
├── static/            # Static files
├── templates/         # HTML templates
└── translations/      # Language translations
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask framework
- BeautifulSoup4 for web scraping
- Selenium for dynamic content
- All job platforms for providing opportunities
