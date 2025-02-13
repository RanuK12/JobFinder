# 🏆 JobConnect - Encuentra Tu Próximo Trabajo

## 📌 Descripción
JobConnect es una plataforma web que conecta candidatos con ofertas laborales en diferentes sectores y regiones. Basándose en tu CV, la aplicación encuentra las mejores oportunidades disponibles en diversas plataformas de empleo.

## 🚀 Características Principales
- ✔️ **Carga de CV Inteligente**: Analiza tu CV en formato PDF o DOCX y extrae palabras clave.
- ✔️ **Scraping de Ofertas**: Busca empleos en múltiples plataformas y los clasifica según la relevancia.
- ✔️ **Postulación Rápida**: Guarda las postulaciones realizadas para hacer seguimiento.
- ✔️ **Interfaz Amigable**: Diseño moderno, optimizado para escritorio y móvil.
- ✔️ **Soporte Multi-idioma**: Disponible en Español e Inglés.

## 📸 Capturas de Pantalla
- 🔹 **Página de Inicio**
  <img src="static/screenshots/home.png" width="80%" alt="Home Page">
- 🔹 **Búsqueda de Trabajos**
  <img src="static/screenshots/results.png" width="80%" alt="Search Results">

## 🛠️ Tecnologías Utilizadas
- 🔹 **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-Babel
- 🔹 **Frontend**: Jinja2, HTML, Tailwind CSS
- 🔹 **Scraping**: BeautifulSoup, Requests
- 🔹 **Base de Datos**: SQLite

## ⚡ Instalación Local
1. Clonar el repositorio
    ```bash
    git clone https://github.com/TU_USUARIO/JobConnect.git
    cd JobConnect
    ```
2. Crear un entorno virtual e instalar dependencias
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # En Windows usa: venv\Scripts\activate
    pip install -r requirements.txt
    ```
3. Configurar la base de datos
    ```bash
    flask db upgrade
    ```
4. Ejecutar la aplicación
    ```bash
    python main.py
    ```
   📌 La app se ejecutará en [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## ☁️ Despliegue en Render (Gratis)
1. Subir el código a GitHub
2. Crear cuenta en Render
3. Nuevo servicio web → Conectar a GitHub
4. Build Command:
    ```bash
    pip install -r requirements.txt
    ```
5. Start Command:
    ```bash
    gunicorn main:app --bind 0.0.0.0:$PORT
    ```
6. Deploy y listo! 🎉

## 💡 Contribuciones
- 🔹 Fork el repositorio
- 🔹 Crea una nueva rama (`git checkout -b feature-nueva`)
- 🔹 Haz cambios y commitea (`git commit -m "Nueva función"`)
- 🔹 Sube los cambios (`git push origin feature-nueva`)
- 🔹 Abre un Pull Request

## 📩 Contacto
📧 ¿Tienes dudas o sugerencias? ¡Contáctame!
- 📌 **Email**: emilioranucoliturletto@gmail.com
- 📌 **LinkedIn**: [Tu Perfil](https://www.linkedin.com)

🎯 **JobConnect - Tu próximo trabajo está a un clic de distancia.** 🚀

🔹 **¿Te gustó el proyecto? Dale ⭐ en GitHub!**
👉 [Repositorio en GitHub](https://github.com/TU_USUARIO/JobConnect)
