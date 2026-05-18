# JobConnect

**Intelligent Job Matching Platform** - Upload your CV and get personalized job recommendations powered by AI-based skill matching.

## Overview

JobConnect is a web application that connects job seekers with remote opportunities. The platform analyzes your CV using natural language processing, extracts relevant skills and keywords, then searches multiple job platforms to find the best matches ranked by relevance.

### Key Features

- **Smart CV Analysis** - Supports PDF and DOCX formats with automatic text extraction and section detection
- **AI-Powered Matching** - Scores and ranks jobs based on skill overlap, role alignment, and keyword relevance
- **Multi-Platform Search** - Scrapes jobs from WeWorkRemotely, RemoteOK, and more
- **Application Tracking** - Save and track your job applications in one place
- **Employer Dashboard** - Post, edit, and manage job listings
- **Multi-language Support** - Available in English, Spanish, and Italian
- **Responsive Design** - Modern UI optimized for desktop and mobile
- **Security** - Password hashing, rate limiting, input validation, and session protection

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask, SQLAlchemy |
| Frontend | Jinja2, Tailwind CSS, Alpine.js |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Scraping | BeautifulSoup, Requests, fake-useragent |
| AI/NLP | Custom keyword extraction & TF-IDF scoring |
| Auth | Flask-Login with bcrypt password hashing |
| i18n | Flask-Babel (ES/EN/IT) |
| Security | Flask-Limiter, CSRF protection |

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/RanuK12/JobFinder.git
cd JobFinder

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your configuration (especially SECRET_KEY)

# 5. Run the application
python app.py
```

The app will be available at **http://localhost:5000**

### First-Time Setup

1. Register a new account (choose "Candidate" or "Employer")
2. As a **Candidate**: Upload your CV (PDF/DOCX) to get job recommendations
3. As an **Employer**: Create job listings from your dashboard

## Project Structure

```
JobFinder/
├── app.py                  # Application factory & routes
├── config.py               # Configuration classes (dev/prod/test)
├── scraper.py              # Multi-platform job scraper
├── cv_parser.py            # CV text extraction (PDF/DOCX)
├── ai_matcher.py           # AI-powered job matching engine
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base layout with navbar & footer
│   ├── navbar.html         # Responsive navigation
│   ├── home.html           # Landing page
│   ├── login.html          # Authentication
│   ├── register.html       # User registration
│   ├── index.html          # CV upload & job search
│   ├── results.html        # Job search results
│   ├── candidate_dashboard.html
│   ├── employer_dashboard.html
│   ├── create_job.html     # Job posting form
│   ├── edit_job.html       # Job editing form
│   ├── job_detail.html     # Job details view
│   ├── applications.html   # Application tracking
│   └── errors/             # Custom error pages (403, 404, 429, 500)
│
├── static/
│   ├── profiles/           # User profile pictures
│   └── logs/               # Application logs
│
├── translations/           # i18n translations (en/es/it)
├── instance/               # SQLite database (auto-created)
└── uploads/                # Temporary CV uploads
```

## Architecture

### Application Design

The application uses Flask's **Application Factory Pattern** for better modularity:

```python
from app import create_app

app = create_app('development')  # or 'production', 'testing'
```

### AI Matching Algorithm

The matching engine uses a multi-factor scoring system:

1. **Skill Matching (60%)** - Compares extracted technical skills against job requirements
2. **Role Alignment (20%)** - Identifies role categories (frontend, backend, data, etc.)
3. **Keyword Overlap (20%)** - General keyword frequency analysis

Jobs are scored 0-100 and labeled as High/Medium/Low relevance.

### Security Features

- Passwords hashed with Werkzeug's `generate_password_hash` (PBKDF2)
- Rate limiting on login (5/min) and registration (3/min) endpoints
- File upload validation (type + size limits)
- Session-based CSRF protection
- Input sanitization on all forms

## Configuration

The app supports three environments via `config.py`:

| Config | Use Case | Debug | Key Differences |
|--------|----------|-------|-----------------|
| `DevelopmentConfig` | Local dev | Yes | Shorter scraping delays, verbose logging |
| `ProductionConfig` | Deployment | No | Proxy support, stricter security |
| `TestingConfig` | Unit tests | Yes | In-memory DB, no rate limits |

Set the environment via `FLASK_ENV` environment variable or pass directly to `create_app()`.

## API Endpoints

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/` | No | Landing page |
| GET/POST | `/login` | No | User login |
| GET/POST | `/register` | No | User registration |
| GET | `/logout` | Yes | Logout |
| GET | `/dashboard` | Yes | Redirect to user dashboard |
| GET/POST | `/search` | Yes | CV upload & job search |
| GET | `/results` | Yes | View matched jobs |
| POST | `/apply_job` | Yes | Save job application (JSON) |
| GET | `/applications` | Yes | View saved applications |
| GET/POST | `/job/create` | Employer | Create job listing |
| GET/POST | `/job/<id>/edit` | Employer | Edit job listing |
| POST | `/job/<id>/delete` | Employer | Delete job listing |
| GET | `/job/<id>` | Yes | Job detail view |
| GET | `/jobs` | No | Public job listings |
| GET | `/set_lang/<lang>` | No | Change language |

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and commit: `git commit -m "Add: description of changes"`
4. Push to your branch: `git push origin feature/my-feature`
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code style
- Add docstrings to all functions and classes
- Keep route handlers concise; extract logic into utility functions
- Use Flask's `flash()` for user feedback messages
- Always validate and sanitize user input

## Deployment

### Production with Gunicorn

```bash
pip install gunicorn
gunicorn "app:create_app('production')" -w 4 -b 0.0.0.0:8000
```

### Environment Variables for Production

```bash
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export DATABASE_URL=postgresql://user:pass@host/dbname
```

## License

This project is licensed under the MIT License.

## Contact

- **Author**: Emilio Ranucoli
- **Email**: ranucoliemilio@gmail.com
- **LinkedIn**: [Emilio Ranucoli](https://www.linkedin.com/in/emilio-ranucoli/)
- **Repository**: [github.com/RanuK12/JobFinder](https://github.com/RanuK12/JobFinder)
