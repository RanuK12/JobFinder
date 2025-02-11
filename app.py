from flask import Flask, request, session, redirect, url_for, render_template
from flask_babel import Babel, gettext as _
from flask_login import LoginManager, UserMixin, login_user, login_required
import os
from scraper import get_jobs
from cv_parser import parse_cv
from ai_matcher import match_jobs

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuración de Babel
babel = Babel(app)
app.config['BABEL_DEFAULT_LOCALE'] = 'es'
LANGUAGES = ['en', 'es', 'it']

@babel.localeselector
def get_locale():
    # 1. Verificar parámetro en la URL
    lang = request.args.get('lang')
    if lang in LANGUAGES:
        session['language'] = lang
        return lang
    
    # 2. Verificar sesión
    if 'language' in session:
        return session['language']
    
    # 3. Usar el del navegador
    return request.accept_languages.best_match(LANGUAGES)

# Configuración de la carpeta de perfiles
app.config['PROFILE_FOLDER'] = os.path.join(app.static_folder, 'profiles')


# Inyectar get_locale en Jinja2
@app.context_processor
def inject_get_locale():
    return dict(get_locale=get_locale)

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in LANGUAGES:
        session['language'] = lang
    return redirect_back()

def redirect_back():
    return redirect(request.referrer or url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['cv']
        continent = request.form.get('continent', 'all')
        
        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            cv_text = parse_cv(filepath)
            jobs = get_jobs(continent, cv_text, get_locale())
            return render_template('results.html', jobs=jobs)
    
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['pdf', 'docx']

if __name__ == '__main__':
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    app.run(debug=True)