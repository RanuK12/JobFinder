from flask import Flask, request, session, redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_babel import Babel, gettext as _
from flask import Flask, request, session, redirect, url_for, render_template, flash, jsonify
from werkzeug.utils import secure_filename
import os
from scraper import get_jobs
from cv_parser import parse_cv

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobconnect.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de la carpeta de archivos
app.config['UPLOAD_FOLDER'] = 'static/profiles'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuración de Flask-Babel
babel = Babel(app)
app.config['BABEL_DEFAULT_LOCALE'] = 'es'
LANGUAGES = ['en', 'es']

@babel.localeselector
def get_locale():
    lang = request.args.get('lang')
    if lang in LANGUAGES:
        session['language'] = lang
        return lang
    if 'language' in session:
        return session['language']
    return request.accept_languages.best_match(LANGUAGES)

# Inyectar idioma en Jinja2
@app.context_processor
def inject_language():
    return dict(current_language=get_locale())

# Inicialización de extensiones
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelo de usuarios
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120))
    profile_picture = db.Column(db.String(200), default='profiles/default-profile.jpg')
    user_type = db.Column(db.String(20), nullable=False)  # candidate/employer
    created_at = db.Column(db.DateTime, default=db.func.now())
    skills = db.Column(db.String(500), default='')  # Inicializa skills como cadena vacía
    
# Añadir este nuevo modelo
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    application_date = db.Column(db.DateTime, default=db.func.now())

# Modelo de trabajos publicados
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(200), nullable=False)
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

# Configuración de Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rutas principales
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        file = request.files['cv']

        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.name)
            file.save(filepath)

            # Extraer texto del CV
            cv_text = parse_cv(filepath)

            # Obtener trabajos basados en el CV
            jobs = get_jobs(cv_text)  # 🔹 Se eliminó el tercer parámetro incorrecto

            if jobs:
                flash(_('Se encontraron trabajos recomendados.'), 'success')
            else:
                flash(_('No se encontraron trabajos que coincidan con tu CV.'), 'info')

            return render_template('results.html', jobs=jobs)

    return render_template('index.html')

@app.route('/results')
@login_required
def results():
    jobs = request.args.getlist('jobs')
    if not jobs:
        jobs = []
    return render_template('results.html', jobs=jobs)

# Autenticación de usuario
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Verificar si el usuario existe
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:  # ⚠️ Mejora: Implementar Hashing de Contraseñas
            login_user(user)
            flash(_('Has iniciado sesión correctamente.'), 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(_('Credenciales inválidas.'), 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        user_type = request.form['user_type']

        # Verificar si el email ya está registrado
        if User.query.filter_by(email=email).first():
            flash(_('El email ya está registrado.'), 'danger')
            return redirect(url_for('register'))

        # Crear nuevo usuario
        new_user = User(
            email=email,
            password=password,
            full_name=full_name,
            user_type=user_type,
            skills=''  # Inicializa skills como cadena vacía
        )
        db.session.add(new_user)
        db.session.commit()

        # Iniciar sesión automáticamente después del registro
        login_user(new_user)
        flash(_('Registro exitoso. Has iniciado sesión correctamente.'), 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

# Panel de usuario
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'candidate':
        return redirect(url_for('candidate_dashboard'))
    elif current_user.user_type == 'employer':
        return redirect(url_for('employer_dashboard'))
    return redirect(url_for('home'))

# Panel del candidato
@app.route('/candidate/dashboard')
@login_required
def candidate_dashboard():
    if current_user.user_type != 'candidate':
        return redirect(url_for('home'))
    return render_template('candidate_dashboard.html')

# Panel del empleador
@app.route('/employer/dashboard')
@login_required
def employer_dashboard():
    if current_user.user_type != 'employer':
        return redirect(url_for('home'))
    jobs = Job.query.filter_by(employer_id=current_user.id).all()
    return render_template('employer_dashboard.html', jobs=jobs)

# Ruta para cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('Has cerrado sesión correctamente.'), 'success')
    return redirect(url_for('home'))

# Validación de archivos permitidos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx'}

# Actualización de perfil
@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    # Actualizar foto de perfil
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            current_user.profile_picture = f'profiles/{filename}'
            
@app.route('/apply_job', methods=['POST'])
@login_required
def apply_job():
    job_data = request.get_json()
    
    existing_application = Application.query.filter_by(
        user_id=current_user.id, 
        job_title=job_data['title'], 
        company=job_data['company']
    ).first()

    if existing_application:
        return jsonify({'status': 'error', 'message': 'Ya aplicaste a este trabajo'})

    new_application = Application(
        user_id=current_user.id,
        job_title=job_data['title'],
        company=job_data['company'],
    )

    db.session.add(new_application)
    db.session.commit()

    return jsonify({'status': 'success'})

@app.route('/applications')
@login_required
def applications():
    if current_user.user_type != 'candidate':
        return redirect(url_for('home'))
    
    user_applications = Application.query.filter_by(
        user_id=current_user.id
    ).order_by(Application.application_date.desc()).all()
    
    return render_template('applications.html', applications=user_applications)
            
    # Actualizar habilidades
    skills = request.form.get('skills', '').strip()
    if skills:
        current_user.skills = ', '.join([skill.strip() for skill in skills.split(',') if skill.strip()])

    db.session.commit()
    flash(_('Perfil actualizado correctamente.'), 'success')
    return redirect(url_for('candidate_dashboard'))

# Crear oferta laboral (para empleadores)
@app.route('/job/create', methods=['GET', 'POST'])
@login_required
def create_job():
    if current_user.user_type != 'employer':
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        description = request.form['description']
        url = request.form['url']

        new_job = Job(
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            employer_id=current_user.id
        )

        db.session.add(new_job)
        db.session.commit()
        flash(_('Oferta laboral creada correctamente.'), 'success')
        return redirect(url_for('employer_dashboard'))

    return render_template('create_job.html')

# Inicialización de la base de datos
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)