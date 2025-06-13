# 🏆 JobConnect - Find Your Next Job

## 📌 Description
JobConnect is a web platform that connects candidates with job opportunities across different sectors and regions. Based on your CV, the application finds the best available opportunities on various job platforms.

## 🚀 Key Features
- ✔️ **Smart CV Upload**: Analyzes your CV in PDF or DOCX format and extracts keywords.
- ✔️ **Job Scraping**: Searches for jobs across multiple platforms (WeWorkRemotely, RemoteOK) and ranks them by relevance.
- ✔️ **Quick Application**: Saves your applications for tracking.
- ✔️ **User-Friendly Interface**: Modern design, optimized for desktop and mobile.
- ✔️ **Multi-language Support**: Available in Spanish, English, and Italian.
- ✔️ **AI-powered job matching**: Intelligent matching system based on AI.
- ✔️ **Rate limiting and caching**: Performance optimization and overload protection.

## 🛠️ Technologies Used
- 🔹 **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-Babel
- 🔹 **Frontend**: Jinja2, HTML, Tailwind CSS
- 🔹 **Scraping**: BeautifulSoup, Selenium, Requests
- 🔹 **Database**: SQLite
- 🔹 **AI**: Natural Language Processing models

## ⚡ Local Installation
1. Clone the repository
    ```bash
    git clone https://github.com/RanuK12/JobFinder.git
    cd Job_finder_app
    ```
2. Create a virtual environment and install dependencies
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    pip install -r requirements.txt
    ```
3. Configure environment variables
    ```bash
    cp .env.example .env
    # Edit .env with your configuration
    ```
4. Run the application
    ```bash
    python app.py
    ```
   📌 The app will run at [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## 📁 Project Structure
```
Job_finder_app/
├── app.py              # Main application file
├── config.py           # Configuration
├── scraper.py          # Scraping module
├── cv_parser.py        # CV analysis module
├── ai_matcher.py       # Matching module
├── requirements.txt    # Dependencies
├── static/            # Static files
├── templates/         # HTML templates
└── translations/      # Translations
```

## 💡 Contributing
- 🔹 Fork the repository
- 🔹 Create a new branch (`git checkout -b feature-new`)
- 🔹 Make changes and commit (`git commit -m "New feature"`)
- 🔹 Push changes (`git push origin feature-new`)
- 🔹 Open a Pull Request

## 📩 Contact
📧 Questions or suggestions? Contact me!
- 📌 **Email**: emilioranucoliturletto@gmail.com
- 📌 **LinkedIn**: [Your Profile](https://www.linkedin.com)

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🎯 **JobConnect - Your next job is just a click away.** 🚀

🔹 **Like the project? Give it a ⭐ on GitHub!**
👉 [GitHub Repository](https://github.com/RanuK12/JobFinder)
