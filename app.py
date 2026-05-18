"""
JobConnect - Main Application Factory

This module creates and configures the Flask application using the
application factory pattern for better testability and modularity.
"""

import os
import logging
from datetime import datetime

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
# Database Models
# =============================================================================

class User(UserMixin, db.Model):
    """User model for authentication and profile management."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    profile_picture = db.Column(
        db.String(200), default='profiles/default-profile.jpg'
    )
    user_type = db.Column(db.String(20), nullable=False)  # candidate/employer
    skills = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
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

    def __repr__(self):
        return f'<User {self.email}>'


class Application(db.Model):
    """Track user job applications."""

    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    job_title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    job_url = db.Column(db.String(500), default='')
    status = db.Column(db.String(20), default='applied')  # applied/interview/rejected/accepted
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, default='')

    def __repr__(self):
        return f'<Application {self.job_title} @ {self.company}>'


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
    job_type = db.Column(db.String(50), default='full-time')  # full-time/part-time/contract
    url = db.Column(db.String(500), default='')
    employer_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
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
        )

    # Initialize extensions with app
    db.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    login_manager.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)

    # Configure login manager
    login_manager.login_view = 'login'
    login_manager.login_message = _('Por favor inicia sesión para acceder a esta página.')
    login_manager.login_message_category = 'warning'

    # Context processors
    @app.context_processor
    def inject_globals():
        """Inject global variables into templates."""
        return {
            'current_language': get_locale(),
            'app_name': app.config['APP_NAME'],
            'now': datetime.utcnow()
        }

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register routes
    _register_routes(app)

    # Register error handlers
    _register_error_handlers(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


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
    @limiter.limit("5 per minute")
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
                login_user(user, remember=request.form.get('remember'))
                flash(_('Has iniciado sesión correctamente.'), 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash(_('Credenciales inválidas. Verifica tu email y contraseña.'), 'danger')

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    @limiter.limit("3 per minute")
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
                skills=''
            )
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)
            flash(_('Registro exitoso. Bienvenido a JobConnect!'), 'success')
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
        if current_user.user_type == 'employer':
            return redirect(url_for('employer_dashboard'))
        return redirect(url_for('candidate_dashboard'))

    @app.route('/candidate/dashboard')
    @login_required
    def candidate_dashboard():
        """Candidate dashboard with profile management."""
        if current_user.user_type != 'candidate':
            abort(403)
        recent_applications = current_user.applications.order_by(
            Application.application_date.desc()
        ).limit(5).all()
        return render_template(
            'candidate_dashboard.html',
            recent_applications=recent_applications
        )

    @app.route('/employer/dashboard')
    @login_required
    def employer_dashboard():
        """Employer dashboard with job management."""
        if current_user.user_type != 'employer':
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
        """CV upload and job search page."""
        if request.method == 'POST':
            if 'cv' not in request.files:
                flash(_('No se seleccionó ningún archivo.'), 'error')
                return redirect(request.url)

            file = request.files['cv']
            if file.filename == '':
                flash(_('No se seleccionó ningún archivo.'), 'error')
                return redirect(request.url)

            if not _allowed_file(file.filename, app):
                flash(
                    _('Tipo de archivo no válido. Sube un archivo PDF o DOCX.'),
                    'error'
                )
                return redirect(request.url)

            filepath = None
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # Parse CV
                from cv_parser import parse_cv
                cv_text = parse_cv(filepath)
                if not cv_text:
                    raise ValueError(_('No se pudo extraer texto del CV.'))

                # Search for jobs
                from scraper import JobScraper
                scraper = JobScraper(app)
                jobs = scraper.get_jobs(cv_text, session.get('language', 'en'))

                # Match jobs with AI
                from ai_matcher import match_jobs
                matched_jobs = match_jobs(cv_text, jobs) if jobs else []

                if matched_jobs:
                    session['matched_jobs'] = matched_jobs
                    flash(
                        _('Se encontraron %(count)s trabajos recomendados.',
                          count=len(matched_jobs)),
                        'success'
                    )
                    return redirect(url_for('results'))
                else:
                    flash(
                        _('No se encontraron trabajos que coincidan con tu CV. '
                          'Intenta actualizar tus habilidades.'),
                        'info'
                    )
                    return redirect(request.url)

            except ValueError as e:
                flash(str(e), 'error')
                return redirect(request.url)
            except Exception as e:
                logger.error(f"Error processing CV: {str(e)}")
                flash(
                    _('Error procesando el archivo. Inténtalo de nuevo.'),
                    'error'
                )
                return redirect(request.url)
            finally:
                # Cleanup uploaded file
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass

        return render_template('index.html')

    @app.route('/results')
    @login_required
    def results():
        """Display job search results."""
        matched_jobs = session.get('matched_jobs', [])
        if not matched_jobs:
            flash(_('No hay resultados. Realiza una nueva búsqueda.'), 'warning')
            return redirect(url_for('index'))
        return render_template('results.html', jobs=matched_jobs)

    # =========================================================================
    # Profile Management
    # =========================================================================

    @app.route('/profile/update', methods=['POST'])
    @login_required
    def update_profile():
        """Update user profile (photo and skills)."""
        # Update profile picture
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                allowed_images = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
                ext = file.filename.rsplit('.', 1)[-1].lower()
                if ext in allowed_images:
                    filename = secure_filename(
                        f"user_{current_user.id}.{ext}"
                    )
                    filepath = os.path.join(
                        'static', 'profiles', filename
                    )
                    file.save(filepath)
                    current_user.profile_picture = f'profiles/{filename}'

        # Update skills
        skills = request.form.get('skills', '').strip()
        if skills:
            cleaned_skills = ', '.join([
                s.strip() for s in skills.split(',') if s.strip()
            ])
            current_user.skills = cleaned_skills

        db.session.commit()
        flash(_('Perfil actualizado correctamente.'), 'success')
        return redirect(url_for('candidate_dashboard'))

    # =========================================================================
    # Application Tracking
    # =========================================================================

    @app.route('/apply_job', methods=['POST'])
    @login_required
    def apply_job():
        """Apply to a job (save application)."""
        if current_user.user_type != 'candidate':
            return jsonify({
                'status': 'error',
                'message': _('Solo los candidatos pueden postular.')
            }), 403

        data = request.get_json()
        if not data or not data.get('title') or not data.get('company'):
            return jsonify({
                'status': 'error',
                'message': _('Datos incompletos.')
            }), 400

        # Check for duplicate application
        existing = Application.query.filter_by(
            user_id=current_user.id,
            job_title=data['title'],
            company=data['company']
        ).first()

        if existing:
            return jsonify({
                'status': 'error',
                'message': _('Ya aplicaste a este trabajo.')
            }), 409

        new_application = Application(
            user_id=current_user.id,
            job_title=data['title'],
            company=data['company'],
            job_url=data.get('url', '')
        )
        db.session.add(new_application)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': _('Postulación registrada exitosamente.')
        })

    @app.route('/applications')
    @login_required
    def applications():
        """View user's job applications."""
        if current_user.user_type != 'candidate':
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
        if current_user.user_type != 'employer':
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
            return redirect(url_for('employer_dashboard'))

        return render_template('create_job.html')

    @app.route('/job/<int:job_id>')
    @login_required
    def job_detail(job_id):
        """View job details."""
        job = Job.query.get_or_404(job_id)
        return render_template('job_detail.html', job=job)

    @app.route('/job/<int:job_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_job(job_id):
        """Edit an existing job listing."""
        job = Job.query.get_or_404(job_id)
        if job.employer_id != current_user.id:
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

            db.session.commit()
            flash(_('Oferta actualizada correctamente.'), 'success')
            return redirect(url_for('employer_dashboard'))

        return render_template('edit_job.html', job=job)

    @app.route('/job/<int:job_id>/delete', methods=['POST'])
    @login_required
    def delete_job(job_id):
        """Delete a job listing."""
        job = Job.query.get_or_404(job_id)
        if job.employer_id != current_user.id:
            abort(403)

        db.session.delete(job)
        db.session.commit()
        flash(_('Oferta eliminada correctamente.'), 'success')
        return redirect(url_for('employer_dashboard'))

    @app.route('/jobs')
    def job_listings():
        """Public job listings page."""
        jobs = Job.query.filter_by(is_active=True).order_by(
            Job.created_at.desc()
        ).all()
        return render_template('job_listings.html', jobs=jobs)


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
