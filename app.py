from flask import Flask, request, session, redirect, url_for, render_template, flash
from flask_babel import Babel, gettext as _
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from werkzeug.utils import secure_filename
from scraper import JobScraper
from cv_parser import parse_cv
from ai_matcher import match_jobs
from config import config

# Initialize Flask extensions
babel = Babel()
login_manager = LoginManager()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)

class User(UserMixin):
    def __init__(self, id, email, full_name, profile_picture=None):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.profile_picture = profile_picture or 'default_profile.png'

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    babel.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'login'
    login_manager.login_message = _('Please log in to access this page.')
    
    @login_manager.user_loader
    def load_user(user_id):
        # Por ahora retornamos None ya que no tenemos sistema de usuarios
        return None
    
    # Initialize job scraper with the app instance
    scraper = JobScraper(app)
    
    @babel.localeselector
    def get_locale():
        # 1. Check URL parameter
        lang = request.args.get('lang')
        if lang in app.config['LANGUAGES']:
            session['language'] = lang
            return lang
        
        # 2. Check session
        if 'language' in session:
            return session['language']
        
        # 3. Use browser's preferred language
        return request.accept_languages.best_match(app.config['LANGUAGES'])
    
    @app.context_processor
    def inject_get_locale():
        return dict(get_locale=get_locale)
    
    @app.route('/set_lang/<lang>')
    def set_lang(lang):
        if lang in app.config['LANGUAGES']:
            session['language'] = lang
        return redirect_back()
    
    def redirect_back():
        return redirect(request.referrer or url_for('index'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            # Por ahora solo redirigimos al index
            return redirect(url_for('index'))
        return render_template('login.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            # Por ahora solo redirigimos al index
            return redirect(url_for('index'))
        return render_template('register.html')
    
    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))
    
    @app.route('/', methods=['GET', 'POST'])
    @limiter.limit("10 per minute")
    def index():
        if request.method == 'POST':
            if 'cv' not in request.files:
                flash(_('No file selected'), 'error')
                return redirect(request.url)
            
            file = request.files['cv']
            if file.filename == '':
                flash(_('No file selected'), 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filepath = None
                try:
                    # Add logging to inspect file and filename before validation
                    app.logger.info(f"File object type: {type(file)}")
                    app.logger.info(f"File filename type: {type(file.filename)}")
                    app.logger.info(f"File filename value: {file.filename}")
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Parse CV and get jobs
                    cv_text = parse_cv(filepath)
                    if not cv_text:
                        raise ValueError("No text content found in CV")
                        
                    jobs = scraper.get_jobs(cv_text, get_locale())
                    
                    if not jobs:
                        flash(_('No jobs found matching your CV'), 'warning')
                        return redirect(request.url)
                    
                    # Match jobs with CV
                    matched_jobs = match_jobs(jobs, cv_text)
                    
                    if not matched_jobs:
                        flash(_('No matching jobs found'), 'warning')
                        return redirect(request.url)
                    
                    # Guardar los trabajos en la sesión para evitar problemas de estado
                    session['matched_jobs'] = matched_jobs
                    return redirect(url_for('results'))
                    
                except ValueError as e:
                    flash(_('Error processing CV: %(error)s', error=str(e)), 'error')
                    return redirect(request.url)
                except Exception as e:
                    flash(_('Error processing file: %(error)s', error=str(e)), 'error')
                    return redirect(request.url)
                finally:
                    # Clean up uploaded file
                    if filepath and os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except Exception as e:
                            app.logger.error(f"Error removing file {filepath}: {str(e)}")
            else:
                flash(_('Invalid file type. Please upload a PDF or DOCX file.'), 'error')
                return redirect(request.url)
        
        return render_template('index.html')
    
    @app.route('/results')
    def results():
        matched_jobs = session.get('matched_jobs', [])
        if not matched_jobs:
            flash(_('No jobs found. Please try again.'), 'warning')
            return redirect(url_for('index'))
        return render_template('results.html', jobs=matched_jobs)
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config['DEBUG'])