"""
JobConnect - Main Application Factory

This module creates and configures the Flask application using the
application factory pattern for better testability and modularity.
"""

import os
import logging
from datetime import datetime, timezone

from flask import (
    Flask, request, session, redirect, url_for,
    render_template, flash, jsonify, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from flask_babel import Babel, gettext as _
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

from config import config

# Initialize extensions (without app binding)
db = SQLAlchemy()
babel = Babel()
login_manager = LoginManager()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Admin Decorator
# =============================================================================

def admin_required(f):
    """Decorator to require admin access for a route."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Database Models
# =============================================================================

class User(UserMixin, db.Model):
    """User model with portfolio-style showcase profile.

    A candidate's profile is their public showcase to recruiters - includes
    bio, headline, location, social links, CV link, work experience, etc.
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    profile_picture = db.Column(
        db.String(200), default='profiles/default-profile.jpg'
    )
    user_type = db.Column(db.String(20), nullable=False)  # candidate/employer/admin
    skills = db.Column(db.Text, default='')
    is_active_user = db.Column(db.Boolean, default=True)

    # Public showcase profile fields
    username = db.Column(db.String(50), unique=True, index=True, nullable=True)
    headline = db.Column(db.String(200), default='')   # e.g. "Senior Python Developer"
    bio = db.Column(db.Text, default='')                # multi-paragraph about
    location = db.Column(db.String(120), default='')    # e.g. "Buenos Aires, Argentina"
    years_experience = db.Column(db.Integer, default=0)
    open_to_work = db.Column(db.Boolean, default=True)  # toggle visibility
    is_public = db.Column(db.Boolean, default=True)     # public profile visibility

    # Social/portfolio links
    linkedin_url = db.Column(db.String(300), default='')
    github_url = db.Column(db.String(300), default='')
    portfolio_url = db.Column(db.String(300), default='')
    twitter_url = db.Column(db.String(300), default='')
    cv_url = db.Column(db.String(300), default='')      # uploaded CV file path

    # Preferences
    preferred_job_type = db.Column(db.String(50), default='')   # fulltime/contract/etc
    preferred_remote = db.Column(db.Boolean, default=False)
    expected_salary = db.Column(db.String(100), default='')      # e.g. "USD 80k-120k"

    # Employer specific
    company_name = db.Column(db.String(150), default='')
    company_website = db.Column(db.String(300), default='')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    applications = db.relationship(
        'Application', backref='user', lazy='dynamic'
    )
    jobs = db.relationship('Job', backref='employer', lazy='dynamic')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def generate_username(self):
        """Generate a URL-safe username from email or full name."""
        import re as _re
        base = (self.full_name or self.email.split('@')[0]).lower()
        slug = _re.sub(r'[^a-z0-9]+', '-', base).strip('-')[:40]
        return slug or f'user{self.id}'

    @property
    def is_admin(self):
        return self.user_type == 'admin'

    @property
    def skill_list(self):
        """Return list of skills, cleaned up."""
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    def __repr__(self):
        return f'<User {self.email}>'


class Application(db.Model):
    """Track user job applications with pipeline states.

    Pipeline states (inspired by career-ops & job-ops):
    - saved: bookmarked for later
    - applied: application submitted
    - contacted: recruiter reached out
    - interviewing: in interview process
    - offer: received an offer
    - accepted: accepted the offer
    - rejected: rejected by company or user declined
    """

    __tablename__ = 'applications'

    PIPELINE_STATES = [
        'saved', 'applied', 'contacted', 'interviewing', 'offer', 'accepted', 'rejected'
    ]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    job_title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    job_url = db.Column(db.String(500), default='')
    status = db.Column(db.String(20), default='saved')
    match_score = db.Column(db.Integer, default=0)  # 0-100
    match_grade = db.Column(db.String(2), default='')  # A-F
    location = db.Column(db.String(200), default='')
    salary_range = db.Column(db.String(100), default='')
    job_type = db.Column(db.String(50), default='')
    platform = db.Column(db.String(50), default='')
    application_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    notes = db.Column(db.Text, default='')

    @property
    def status_color(self):
        """Return CSS color class for the current status."""
        colors = {
            'saved': 'gray',
            'applied': 'blue',
            'contacted': 'purple',
            'interviewing': 'yellow',
            'offer': 'green',
            'accepted': 'emerald',
            'rejected': 'red',
        }
        return colors.get(self.status, 'gray')

    @property
    def status_icon(self):
        """Return FontAwesome icon for the current status."""
        icons = {
            'saved': 'fa-bookmark',
            'applied': 'fa-paper-plane',
            'contacted': 'fa-envelope',
            'interviewing': 'fa-comments',
            'offer': 'fa-trophy',
            'accepted': 'fa-check-circle',
            'rejected': 'fa-times-circle',
        }
        return icons.get(self.status, 'fa-circle')

    def __repr__(self):
        return f'<Application {self.job_title} @ {self.company} [{self.status}]>'


class Job(db.Model):
    """Employer-posted job listings."""

    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False, default='Remote')
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, default='')
    salary_range = db.Column(db.String(100), default='')
    job_type = db.Column(db.String(50), default='full-time')
    url = db.Column(db.String(500), default='')
    employer_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f'<Job {self.title} @ {self.company}>'



# =============================================================================
# Application Factory
# =============================================================================

def create_app(config_name=None):
    """
    Create and configure the Flask application.

    Args:
        config_name: Configuration to use ('development', 'production', 'testing')

    Returns:
        Configured Flask application instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Define locale selector for Babel 4.0
    def get_locale():
        """Determine the best language for the user."""
        lang = request.args.get('lang')
        if lang and lang in app.config['LANGUAGES']:
            session['language'] = lang
            return lang
        if 'language' in session:
            return session['language']
        return request.accept_languages.best_match(
            app.config['LANGUAGES'].keys()
        ) or 'es'

    # Initialize extensions with app
    db.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    login_manager.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)

    # Configure login manager
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    # Context processors
    @app.context_processor
    def inject_globals():
        """Inject global variables into templates."""
        return {
            'current_language': get_locale(),
            'app_name': app.config['APP_NAME'],
            'now': datetime.now(timezone.utc)
        }

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register routes
    _register_routes(app)

    # Register admin routes
    _register_admin_routes(app)

    # Register error handlers
    _register_error_handlers(app)

    # Create database tables and ensure admin exists
    with app.app_context():
        db.create_all()
        _migrate_database()
        _ensure_admin_exists()

    return app


def _migrate_database():
    """Add missing columns to existing PostgreSQL tables.
    
    db.create_all() only creates new tables, it won't add columns
    to tables that already exist. This handles schema migrations.
    """
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(db.engine)

        # Users table migrations - adds new profile showcase columns
        if 'users' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('users')]
            user_migrations = {
                'is_active_user': 'ALTER TABLE users ADD COLUMN is_active_user BOOLEAN DEFAULT TRUE',
                'username': 'ALTER TABLE users ADD COLUMN username VARCHAR(50) UNIQUE',
                'headline': "ALTER TABLE users ADD COLUMN headline VARCHAR(200) DEFAULT ''",
                'bio': "ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''",
                'location': "ALTER TABLE users ADD COLUMN location VARCHAR(120) DEFAULT ''",
                'years_experience': 'ALTER TABLE users ADD COLUMN years_experience INTEGER DEFAULT 0',
                'open_to_work': 'ALTER TABLE users ADD COLUMN open_to_work BOOLEAN DEFAULT TRUE',
                'is_public': 'ALTER TABLE users ADD COLUMN is_public BOOLEAN DEFAULT TRUE',
                'linkedin_url': "ALTER TABLE users ADD COLUMN linkedin_url VARCHAR(300) DEFAULT ''",
                'github_url': "ALTER TABLE users ADD COLUMN github_url VARCHAR(300) DEFAULT ''",
                'portfolio_url': "ALTER TABLE users ADD COLUMN portfolio_url VARCHAR(300) DEFAULT ''",
                'twitter_url': "ALTER TABLE users ADD COLUMN twitter_url VARCHAR(300) DEFAULT ''",
                'cv_url': "ALTER TABLE users ADD COLUMN cv_url VARCHAR(300) DEFAULT ''",
                'preferred_job_type': "ALTER TABLE users ADD COLUMN preferred_job_type VARCHAR(50) DEFAULT ''",
                'preferred_remote': 'ALTER TABLE users ADD COLUMN preferred_remote BOOLEAN DEFAULT FALSE',
                'expected_salary': "ALTER TABLE users ADD COLUMN expected_salary VARCHAR(100) DEFAULT ''",
                'company_name': "ALTER TABLE users ADD COLUMN company_name VARCHAR(150) DEFAULT ''",
                'company_website': "ALTER TABLE users ADD COLUMN company_website VARCHAR(300) DEFAULT ''",
            }
            with db.engine.connect() as conn:
                for col_name, sql in user_migrations.items():
                    if col_name not in columns:
                        try:
                            conn.execute(text(sql))
                            logger.info(f"Migration: Added users.{col_name}")
                        except Exception as e:
                            logger.debug(f"Skip users.{col_name}: {e}")
                conn.commit()

            # Backfill usernames for existing users
            users_no_username = User.query.filter(
                (User.username == None) | (User.username == '')  # noqa: E711
            ).all()
            for user in users_no_username:
                base = user.generate_username()
                # Ensure uniqueness
                username = base
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base}-{counter}"
                    counter += 1
                user.username = username
            if users_no_username:
                db.session.commit()
                logger.info(f"Backfilled {len(users_no_username)} usernames")

        # Applications table migrations
        if 'applications' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('applications')]
            migrations = {
                'match_score': 'ALTER TABLE applications ADD COLUMN match_score INTEGER DEFAULT 0',
                'match_grade': "ALTER TABLE applications ADD COLUMN match_grade VARCHAR(2) DEFAULT ''",
                'location': "ALTER TABLE applications ADD COLUMN location VARCHAR(200) DEFAULT ''",
                'salary_range': "ALTER TABLE applications ADD COLUMN salary_range VARCHAR(100) DEFAULT ''",
                'job_type': "ALTER TABLE applications ADD COLUMN job_type VARCHAR(50) DEFAULT ''",
                'platform': "ALTER TABLE applications ADD COLUMN platform VARCHAR(50) DEFAULT ''",
                'updated_at': 'ALTER TABLE applications ADD COLUMN updated_at TIMESTAMP',
            }
            with db.engine.connect() as conn:
                for col_name, sql in migrations.items():
                    if col_name not in columns:
                        try:
                            conn.execute(text(sql))
                            logger.info(f"Migration: Added applications.{col_name}")
                        except Exception:
                            pass  # Column might already exist
                conn.commit()

    except Exception as e:
        logger.warning(f"Migration check skipped: {e}")


def _ensure_admin_exists():
    """Create default admin user if none exists."""
    admin = User.query.filter_by(user_type='admin').first()
    if not admin:
        admin = User(
            email='admin@jobconnect.com',
            full_name='Administrador',
            user_type='admin',
            skills='',
            is_active_user=True,
            username='admin',
            headline='Administrator',
            is_public=False,
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
        try:
            db.session.commit()
            logger.info("Admin user created: admin@jobconnect.com / Admin123!")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating admin user: {e}")



# =============================================================================
# Route Registration
# =============================================================================

def _register_routes(app):
    """Register all application routes."""

    @app.route('/')
    def home():
        """Landing page."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('home.html')

    @app.route('/set_lang/<lang>')
    def set_lang(lang):
        """Change the application language."""
        if lang in app.config['LANGUAGES']:
            session['language'] = lang
        return redirect(request.referrer or url_for('home'))

    # =========================================================================
    # Authentication Routes
    # =========================================================================

    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit("10 per minute")
    def login():
        """User login."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            if not email or not password:
                flash(_('Por favor completa todos los campos.'), 'warning')
                return render_template('login.html')

            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                if hasattr(user, 'is_active_user') and not user.is_active_user:
                    flash(_('Tu cuenta ha sido desactivada. Contacta al administrador.'), 'danger')
                    return render_template('login.html')
                login_user(user, remember=True)  # Always remember
                session.permanent = True
                flash(_('Has iniciado sesión correctamente.'), 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash(_('Credenciales inválidas. Verifica tu email y contraseña.'), 'danger')

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    @limiter.limit("5 per minute")
    def register():
        """User registration."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            full_name = request.form.get('full_name', '').strip()
            user_type = request.form.get('user_type', 'candidate')

            # Validation
            errors = []
            if not email or not password or not full_name:
                errors.append(_('Todos los campos son obligatorios.'))
            if password != confirm_password:
                errors.append(_('Las contraseñas no coinciden.'))
            if len(password) < 8:
                errors.append(_('La contraseña debe tener al menos 8 caracteres.'))
            if user_type not in ('candidate', 'employer'):
                errors.append(_('Tipo de usuario inválido.'))
            if User.query.filter_by(email=email).first():
                errors.append(_('El email ya está registrado.'))

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('register.html')

            # Create user
            new_user = User(
                email=email,
                full_name=full_name,
                user_type=user_type,
                skills='',
                is_active_user=True
            )
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.flush()  # Get the user ID before commit

            # Assign a unique username from the user's name
            base = new_user.generate_username()
            username = base
            counter = 1
            while User.query.filter(User.username == username,
                                    User.id != new_user.id).first():
                username = f"{base}-{counter}"
                counter += 1
            new_user.username = username

            db.session.commit()

            login_user(new_user)
            flash(_('Registro exitoso. ¡Bienvenido a JobConnect!'), 'success')
            return redirect(url_for('dashboard'))

        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        """User logout."""
        logout_user()
        flash(_('Has cerrado sesión correctamente.'), 'success')
        return redirect(url_for('home'))

    # =========================================================================
    # Dashboard Routes
    # =========================================================================

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Redirect to appropriate dashboard based on user type."""
        if current_user.user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        if current_user.user_type == 'employer':
            return redirect(url_for('employer_dashboard'))
        return redirect(url_for('candidate_dashboard'))

    @app.route('/candidate/dashboard')
    @login_required
    def candidate_dashboard():
        """Candidate dashboard with pipeline overview."""
        if current_user.user_type not in ('candidate', 'admin'):
            abort(403)
        recent_applications = current_user.applications.order_by(
            Application.application_date.desc()
        ).all()
        return render_template(
            'candidate_dashboard.html',
            recent_applications=recent_applications
        )

    @app.route('/employer/dashboard')
    @login_required
    def employer_dashboard():
        """Employer dashboard with job management."""
        if current_user.user_type not in ('employer', 'admin'):
            abort(403)
        jobs = current_user.jobs.order_by(Job.created_at.desc()).all()
        return render_template('employer_dashboard.html', jobs=jobs)

    # =========================================================================
    # Job Search Routes
    # =========================================================================

    @app.route('/search', methods=['GET', 'POST'])
    @login_required
    @limiter.limit("10 per minute")
    def index():
        """Job search page - supports CV upload and keyword search."""
        if request.method == 'POST':
            search_term = request.form.get('search_term', '').strip()
            location = request.form.get('location', '').strip()
            job_type = request.form.get('job_type', '').strip()
            is_remote = request.form.get('is_remote') == 'on'
            country = request.form.get('country', '').strip()
            cv_text = None
            filepath = None

            # Handle CV upload (optional)
            if 'cv' in request.files:
                file = request.files['cv']
                if file and file.filename and file.filename != '':
                    if not _allowed_file(file.filename, app):
                        flash(
                            _('Tipo de archivo no válido. Sube un archivo PDF o DOCX.'),
                            'error'
                        )
                        return redirect(request.url)

                    try:
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)

                        from cv_parser import parse_cv
                        cv_text = parse_cv(filepath)
                        if cv_text:
                            logger.info(f"CV parsed: {len(cv_text)} chars")
                        else:
                            flash(_('No se pudo extraer texto del CV. Usa la búsqueda por palabras clave.'), 'warning')
                    except Exception as e:
                        logger.error(f"Error parsing CV: {str(e)}")
                        flash(_('Error procesando el CV. Usa la búsqueda por palabras clave.'), 'warning')
                    finally:
                        if filepath and os.path.exists(filepath):
                            try:
                                os.remove(filepath)
                            except OSError:
                                pass

            # Must have either search_term or CV
            if not search_term and not cv_text:
                flash(_('Ingresa un término de búsqueda o sube tu CV.'), 'warning')
                return redirect(request.url)

            try:
                from scraper import JobScraper
                scraper = JobScraper(app)

                # Search for jobs
                jobs = scraper.get_jobs(
                    cv_text=cv_text,
                    language=session.get('language', 'es'),
                    search_term=search_term or None,
                    location=location or None,
                    job_type=job_type or None,
                    is_remote=is_remote,
                    results_wanted=app.config.get('JOBSPY_RESULTS_WANTED', 25),
                    hours_old=app.config.get('JOBSPY_HOURS_OLD', 168),
                    country=country or None,
                )

                if jobs:
                    # If CV was provided, rank by relevance
                    if cv_text:
                        from ai_matcher import match_jobs
                        matched_jobs = match_jobs(cv_text, jobs)
                        if not matched_jobs:
                            matched_jobs = jobs  # Show unranked if matching fails
                    else:
                        matched_jobs = jobs

                    # Store results in server-side cache (not cookie) keyed by user
                    matched_jobs = matched_jobs[:50]
                    cache_key = f'matched_jobs_user_{current_user.id}'
                    cache.set(cache_key, matched_jobs, timeout=3600)
                    flash(
                        _('Se encontraron %(count)s trabajos.',
                          count=len(matched_jobs)),
                        'success'
                    )
                    return redirect(url_for('results'))
                else:
                    flash(
                        _('No se encontraron trabajos. Intenta con otros términos de búsqueda o una ubicación diferente.'),
                        'info'
                    )
                    return redirect(request.url)

            except Exception as e:
                logger.error(f"Error in job search: {str(e)}")
                flash(
                    _('Error en la búsqueda. Inténtalo de nuevo en unos momentos.'),
                    'error'
                )
                return redirect(request.url)

        return render_template('index.html')

    @app.route('/results')
    @login_required
    def results():
        """Display job search results."""
        cache_key = f'matched_jobs_user_{current_user.id}'
        matched_jobs = cache.get(cache_key) or []
        if not matched_jobs:
            flash(_('No hay resultados. Realiza una nueva búsqueda.'), 'warning')
            return redirect(url_for('index'))
        return render_template('results.html', jobs=matched_jobs)

    # =========================================================================
    # Profile Management
    # =========================================================================

    @app.route('/profile/edit', methods=['GET'])
    @login_required
    def edit_profile():
        """Render the profile editor page."""
        return render_template('profile_edit.html', user=current_user)

    @app.route('/profile/update', methods=['POST'])
    @login_required
    def update_profile():
        """Update user profile - all fields."""
        # Profile picture
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                allowed_images = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
                ext = file.filename.rsplit('.', 1)[-1].lower()
                if ext in allowed_images:
                    filename = secure_filename(
                        f"user_{current_user.id}.{ext}"
                    )
                    profiles_dir = os.path.join('static', 'profiles')
                    os.makedirs(profiles_dir, exist_ok=True)
                    filepath = os.path.join(profiles_dir, filename)
                    file.save(filepath)
                    current_user.profile_picture = f'profiles/{filename}'

        # CV upload (saved permanently, not deleted)
        if 'cv_file' in request.files:
            cv_file = request.files['cv_file']
            if cv_file and cv_file.filename:
                allowed_cv = {'pdf', 'docx'}
                ext = cv_file.filename.rsplit('.', 1)[-1].lower()
                if ext in allowed_cv:
                    cv_filename = secure_filename(
                        f"cv_user_{current_user.id}.{ext}"
                    )
                    cvs_dir = os.path.join('static', 'profiles', 'cv')
                    os.makedirs(cvs_dir, exist_ok=True)
                    cv_filepath = os.path.join(cvs_dir, cv_filename)
                    cv_file.save(cv_filepath)
                    current_user.cv_url = f'profiles/cv/{cv_filename}'

        # Text fields - basic info
        if 'full_name' in request.form:
            full_name = request.form.get('full_name', '').strip()
            if full_name:
                current_user.full_name = full_name

        # Username (must be unique, URL-safe)
        if 'username' in request.form:
            new_username = request.form.get('username', '').strip().lower()
            if new_username and new_username != current_user.username:
                import re as _re
                slug = _re.sub(r'[^a-z0-9-]', '', new_username)[:50]
                if slug and slug != current_user.username:
                    existing = User.query.filter(
                        User.username == slug,
                        User.id != current_user.id
                    ).first()
                    if existing:
                        flash(_('Ese nombre de usuario ya está en uso.'), 'warning')
                    else:
                        current_user.username = slug

        # Showcase fields
        for field in [
            'headline', 'bio', 'location',
            'linkedin_url', 'github_url', 'portfolio_url', 'twitter_url',
            'preferred_job_type', 'expected_salary',
            'company_name', 'company_website'
        ]:
            if field in request.form:
                value = request.form.get(field, '').strip()
                setattr(current_user, field, value)

        # Numeric / boolean
        if 'years_experience' in request.form:
            try:
                current_user.years_experience = int(
                    request.form.get('years_experience', 0) or 0
                )
            except ValueError:
                current_user.years_experience = 0

        current_user.open_to_work = request.form.get('open_to_work') == 'on'
        current_user.is_public = request.form.get('is_public') == 'on'
        current_user.preferred_remote = request.form.get('preferred_remote') == 'on'

        # Skills
        skills = request.form.get('skills', '').strip()
        if skills:
            cleaned_skills = ', '.join([
                s.strip() for s in skills.split(',') if s.strip()
            ])
            current_user.skills = cleaned_skills

        try:
            db.session.commit()
            flash(_('Perfil actualizado correctamente.'), 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Profile update error: {e}")
            flash(_('Error al actualizar el perfil.'), 'danger')

        # Redirect back to profile editor unless coming from elsewhere
        next_page = request.form.get('next')
        if next_page == 'public' and current_user.username:
            return redirect(url_for('public_profile', username=current_user.username))
        return redirect(url_for('edit_profile'))

    @app.route('/u/<username>')
    def public_profile(username):
        """Public profile showcase - viewable without login.

        This is the candidate's portfolio page - their public 'storefront'
        for recruiters and the world. Inspired by linkedin/github profiles.
        """
        user = User.query.filter_by(username=username).first_or_404()

        # Privacy check: profile must be public OR viewer must be the owner
        is_owner = current_user.is_authenticated and current_user.id == user.id
        is_admin_viewer = (
            current_user.is_authenticated and current_user.user_type == 'admin'
        )
        if not user.is_public and not (is_owner or is_admin_viewer):
            abort(404)

        # If candidate, show their public job postings (none) + showcase
        # If employer, show their company info + active jobs
        public_jobs = []
        if user.user_type == 'employer':
            public_jobs = Job.query.filter_by(
                employer_id=user.id, is_active=True
            ).order_by(Job.created_at.desc()).all()

        return render_template(
            'public_profile.html',
            user=user,
            is_owner=is_owner,
            public_jobs=public_jobs,
        )

    @app.route('/profile')
    @login_required
    def my_profile():
        """Redirect to current user's public profile."""
        if not current_user.username:
            return redirect(url_for('edit_profile'))
        return redirect(url_for('public_profile', username=current_user.username))

    # =========================================================================
    # Application Tracking
    # =========================================================================

    @app.route('/apply_job', methods=['POST'])
    @login_required
    def apply_job():
        """Save a job to pipeline (bookmark/apply)."""
        if current_user.user_type not in ('candidate', 'admin'):
            return jsonify({
                'status': 'error',
                'message': _('Solo los candidatos pueden guardar trabajos.')
            }), 403

        data = request.get_json()
        if not data or not data.get('title') or not data.get('company'):
            return jsonify({
                'status': 'error',
                'message': _('Datos incompletos.')
            }), 400

        existing = Application.query.filter_by(
            user_id=current_user.id,
            job_title=data['title'],
            company=data['company']
        ).first()

        if existing:
            return jsonify({
                'status': 'error',
                'message': _('Este trabajo ya está en tu pipeline.')
            }), 409

        new_application = Application(
            user_id=current_user.id,
            job_title=data['title'],
            company=data['company'],
            job_url=data.get('url', ''),
            status=data.get('status', 'saved'),
            match_score=int(data.get('match_score', 0) or 0),
            match_grade=data.get('match_grade', ''),
            location=data.get('location', ''),
            salary_range=data.get('salary_range', ''),
            job_type=data.get('job_type', ''),
            platform=data.get('platform', ''),
        )
        db.session.add(new_application)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': _('Trabajo guardado en tu pipeline.')
        })

    @app.route('/application/<int:app_id>/status', methods=['POST'])
    @login_required
    def update_application_status(app_id):
        """Update application pipeline status."""
        application = Application.query.get_or_404(app_id)
        if application.user_id != current_user.id and current_user.user_type != 'admin':
            abort(403)

        data = request.get_json() if request.is_json else None
        new_status = (data.get('status') if data else request.form.get('status', '')).strip()

        if new_status not in Application.PIPELINE_STATES:
            if request.is_json:
                return jsonify({'status': 'error', 'message': _('Estado inválido.')}), 400
            flash(_('Estado inválido.'), 'danger')
            return redirect(url_for('applications'))

        application.status = new_status
        notes = (data.get('notes') if data else request.form.get('notes', '')) or ''
        if notes:
            application.notes = notes

        db.session.commit()

        if request.is_json:
            return jsonify({'status': 'success', 'message': _('Estado actualizado.')})
        flash(_('Estado actualizado.'), 'success')
        return redirect(url_for('applications'))

    @app.route('/application/<int:app_id>/delete', methods=['POST'])
    @login_required
    def delete_application(app_id):
        """Delete an application from pipeline."""
        application = Application.query.get_or_404(app_id)
        if application.user_id != current_user.id and current_user.user_type != 'admin':
            abort(403)

        db.session.delete(application)
        db.session.commit()
        flash(_('Eliminado de tu pipeline.'), 'success')
        return redirect(url_for('applications'))

    @app.route('/applications')
    @login_required
    def applications():
        """View user's job applications."""
        if current_user.user_type not in ('candidate', 'admin'):
            abort(403)

        user_applications = current_user.applications.order_by(
            Application.application_date.desc()
        ).all()
        return render_template(
            'applications.html', applications=user_applications
        )

    # =========================================================================
    # Employer Job Management
    # =========================================================================

    @app.route('/job/create', methods=['GET', 'POST'])
    @login_required
    def create_job():
        """Create a new job listing."""
        if current_user.user_type not in ('employer', 'admin'):
            abort(403)

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            company = request.form.get('company', '').strip()
            location = request.form.get('location', '').strip()
            description = request.form.get('description', '').strip()
            requirements = request.form.get('requirements', '').strip()
            salary_range = request.form.get('salary_range', '').strip()
            job_type = request.form.get('job_type', 'full-time')
            url = request.form.get('url', '').strip()

            if not all([title, company, description]):
                flash(_('Título, empresa y descripción son obligatorios.'), 'danger')
                return render_template('create_job.html')

            new_job = Job(
                title=title,
                company=company,
                location=location or 'Remote',
                description=description,
                requirements=requirements,
                salary_range=salary_range,
                job_type=job_type,
                url=url,
                employer_id=current_user.id
            )
            db.session.add(new_job)
            db.session.commit()

            flash(_('Oferta laboral creada correctamente.'), 'success')
            return redirect(url_for('employer_dashboard') if current_user.user_type == 'employer' else url_for('admin_jobs'))

        return render_template('create_job.html')

    @app.route('/job/<int:job_id>')
    def job_detail(job_id):
        """View job details."""
        job = Job.query.get_or_404(job_id)
        return render_template('job_detail.html', job=job)

    @app.route('/job/<int:job_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_job(job_id):
        """Edit an existing job listing."""
        job = Job.query.get_or_404(job_id)
        if job.employer_id != current_user.id and current_user.user_type != 'admin':
            abort(403)

        if request.method == 'POST':
            job.title = request.form.get('title', job.title).strip()
            job.company = request.form.get('company', job.company).strip()
            job.location = request.form.get('location', job.location).strip()
            job.description = request.form.get('description', job.description).strip()
            job.requirements = request.form.get('requirements', job.requirements).strip()
            job.salary_range = request.form.get('salary_range', job.salary_range).strip()
            job.job_type = request.form.get('job_type', job.job_type)
            job.url = request.form.get('url', job.url).strip()
            job.is_active = 'is_active' in request.form

            db.session.commit()
            flash(_('Oferta actualizada correctamente.'), 'success')
            if current_user.user_type == 'admin':
                return redirect(url_for('admin_jobs'))
            return redirect(url_for('employer_dashboard'))

        return render_template('edit_job.html', job=job)

    @app.route('/job/<int:job_id>/delete', methods=['POST'])
    @login_required
    def delete_job(job_id):
        """Delete a job listing."""
        job = Job.query.get_or_404(job_id)
        if job.employer_id != current_user.id and current_user.user_type != 'admin':
            abort(403)

        db.session.delete(job)
        db.session.commit()
        flash(_('Oferta eliminada correctamente.'), 'success')
        if current_user.user_type == 'admin':
            return redirect(url_for('admin_jobs'))
        return redirect(url_for('employer_dashboard'))

    @app.route('/jobs')
    def job_listings():
        """Public job listings page."""
        jobs = Job.query.filter_by(is_active=True).order_by(
            Job.created_at.desc()
        ).all()
        return render_template('job_listings.html', jobs=jobs)



# =============================================================================
# Admin Routes
# =============================================================================

def _register_admin_routes(app):
    """Register admin panel routes."""

    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        """Admin dashboard with system overview."""
        total_users = User.query.count()
        total_candidates = User.query.filter_by(user_type='candidate').count()
        total_employers = User.query.filter_by(user_type='employer').count()
        total_jobs = Job.query.count()
        active_jobs = Job.query.filter_by(is_active=True).count()
        total_applications = Application.query.count()
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()

        return render_template('admin/dashboard.html',
            total_users=total_users,
            total_candidates=total_candidates,
            total_employers=total_employers,
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            total_applications=total_applications,
            recent_users=recent_users,
            recent_jobs=recent_jobs
        )

    @app.route('/admin/users')
    @admin_required
    def admin_users():
        """Manage all users."""
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin/users.html', users=users)

    @app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
    @admin_required
    def admin_toggle_user(user_id):
        """Activate/deactivate a user."""
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash(_('No puedes desactivar tu propia cuenta.'), 'danger')
            return redirect(url_for('admin_users'))
        user.is_active_user = not user.is_active_user
        db.session.commit()
        status = _('activado') if user.is_active_user else _('desactivado')
        flash(f'Usuario {user.full_name} {status}.', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_user(user_id):
        """Delete a user and their data."""
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash(_('No puedes eliminar tu propia cuenta.'), 'danger')
            return redirect(url_for('admin_users'))
        # Delete related data
        Application.query.filter_by(user_id=user.id).delete()
        Job.query.filter_by(employer_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario {user.full_name} eliminado.', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/change-type', methods=['POST'])
    @admin_required
    def admin_change_user_type(user_id):
        """Change a user's type."""
        user = User.query.get_or_404(user_id)
        new_type = request.form.get('user_type', '')
        if new_type in ('candidate', 'employer', 'admin'):
            user.user_type = new_type
            db.session.commit()
            flash(f'Tipo de usuario cambiado a {new_type}.', 'success')
        else:
            flash(_('Tipo de usuario inválido.'), 'danger')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
    @admin_required
    def admin_reset_password(user_id):
        """Reset a user's password."""
        user = User.query.get_or_404(user_id)
        new_password = request.form.get('new_password', '').strip()
        if len(new_password) < 8:
            flash(_('La contraseña debe tener al menos 8 caracteres.'), 'danger')
            return redirect(url_for('admin_users'))
        user.set_password(new_password)
        db.session.commit()
        flash(f'Contraseña de {user.full_name} actualizada.', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/jobs')
    @admin_required
    def admin_jobs():
        """Manage all jobs."""
        jobs = Job.query.order_by(Job.created_at.desc()).all()
        return render_template('admin/jobs.html', jobs=jobs)

    @app.route('/admin/jobs/<int:job_id>/toggle', methods=['POST'])
    @admin_required
    def admin_toggle_job(job_id):
        """Activate/deactivate a job."""
        job = Job.query.get_or_404(job_id)
        job.is_active = not job.is_active
        db.session.commit()
        status = _('activada') if job.is_active else _('desactivada')
        flash(f'Oferta "{job.title}" {status}.', 'success')
        return redirect(url_for('admin_jobs'))

    @app.route('/admin/applications')
    @admin_required
    def admin_applications():
        """View all applications."""
        all_applications = Application.query.order_by(
            Application.application_date.desc()
        ).all()
        return render_template('admin/applications.html', applications=all_applications)

    @app.route('/admin/create-user', methods=['GET', 'POST'])
    @admin_required
    def admin_create_user():
        """Admin creates a new user."""
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '').strip()
            full_name = request.form.get('full_name', '').strip()
            user_type = request.form.get('user_type', 'candidate')

            if not email or not password or not full_name:
                flash(_('Todos los campos son obligatorios.'), 'danger')
                return render_template('admin/create_user.html')

            if User.query.filter_by(email=email).first():
                flash(_('El email ya está registrado.'), 'danger')
                return render_template('admin/create_user.html')

            if len(password) < 8:
                flash(_('La contraseña debe tener al menos 8 caracteres.'), 'danger')
                return render_template('admin/create_user.html')

            new_user = User(
                email=email,
                full_name=full_name,
                user_type=user_type,
                skills='',
                is_active_user=True
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash(f'Usuario {full_name} creado exitosamente.', 'success')
            return redirect(url_for('admin_users'))

        return render_template('admin/create_user.html')



# =============================================================================
# Error Handlers
# =============================================================================

def _register_error_handlers(app):
    """Register custom error handlers."""

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template('errors/429.html'), 429


# =============================================================================
# Utility Functions
# =============================================================================

def _allowed_file(filename, app):
    """Check if a file has an allowed extension."""
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    )


# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config.get('DEBUG', False), port=5000)
