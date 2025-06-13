# 🏆 JobConnect - Encuentra Tu Próximo Trabajo

## 📌 Descripción
JobConnect es una plataforma web que conecta candidatos con ofertas laborales en diferentes sectores y regiones. Basándose en tu CV, la aplicación encuentra las mejores oportunidades disponibles en diversas plataformas de empleo.

## 🚀 Características Principales
- ✔️ **Carga de CV Inteligente**: Analiza tu CV en formato PDF o DOCX y extrae palabras clave.
- ✔️ **Scraping de Ofertas**: Busca empleos en múltiples plataformas (WeWorkRemotely, RemoteOK) y los clasifica según la relevancia.
- ✔️ **Postulación Rápida**: Guarda las postulaciones realizadas para hacer seguimiento.
- ✔️ **Interfaz Amigable**: Diseño moderno, optimizado para escritorio y móvil.
- ✔️ **Soporte Multi-idioma**: Disponible en Español, Inglés e Italiano.
- ✔️ **AI-powered job matching**: Sistema de emparejamiento inteligente basado en IA.
- ✔️ **Rate limiting y caching**: Optimización de rendimiento y protección contra sobrecarga.

## 🛠️ Tecnologías Utilizadas
- 🔹 **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-Babel
- 🔹 **Frontend**: Jinja2, HTML, Tailwind CSS
- 🔹 **Scraping**: BeautifulSoup, Selenium, Requests
- 🔹 **Base de Datos**: SQLite
- 🔹 **IA**: Modelos de procesamiento de lenguaje natural

## ⚡ Instalación Local
1. Clonar el repositorio
    ```bash
    git clone https://github.com/RanuK12/JobFinder.git
    cd Job_finder_app
    ```
2. Crear un entorno virtual e instalar dependencias
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows usa: venv\Scripts\activate
    pip install -r requirements.txt
    ```
3. Configurar variables de entorno
    ```bash
    cp .env.example .env
    # Editar .env con tu configuración
    ```
4. Ejecutar la aplicación
    ```bash
    python app.py
    ```
   📌 La app se ejecutará en [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## 📁 Estructura del Proyecto
```
Job_finder_app/
├── app.py              # Archivo principal de la aplicación
├── config.py           # Configuración
├── scraper.py          # Módulo de scraping
├── cv_parser.py        # Módulo de análisis de CV
├── ai_matcher.py       # Módulo de emparejamiento
├── requirements.txt    # Dependencias
├── static/            # Archivos estáticos
├── templates/         # Plantillas HTML
└── translations/      # Traducciones
```

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

## 📄 Licencia
Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

🎯 **JobConnect - Tu próximo trabajo está a un clic de distancia.** 🚀

🔹 **¿Te gustó el proyecto? Dale ⭐ en GitHub!**
👉 [Repositorio en GitHub](https://github.com/RanuK12/JobFinder)
