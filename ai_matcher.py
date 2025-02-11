from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import re

def match_jobs(cv_text, jobs):
    cv_keywords = extract_keywords(cv_text)
    matched_jobs = []

    for job in jobs:
        job_text = f"{job['title']} {job['company']} {job['location']}".lower()
        job_keywords = extract_keywords(job_text)

        common = set(cv_keywords).intersection(job_keywords)
        if common:
            matched_jobs.append({
                **job,
                'reasons': [
                    f"{'Habilidades coincidentes' if detect_language(cv_text) == 'es' else 'Matching skills'}: {', '.join(common)}"
                ]
            })

    return matched_jobs

def extract_keywords(text):
    sector_keywords = {
        'programming': ['python', 'java', 'javascript', 'react', 'node', 'programación', 'desarrollo'],
        'engineering': ['engineer', 'mechanical', 'civil', 'ingeniería', 'mecánica'],
        'healthcare': ['doctor', 'nurse', 'medical', 'médico', 'enfermería'],
        'logistics': ['logistics', 'supply chain', 'warehouse', 'logística', 'almacén'],
        'hospitality': ['hotel', 'restaurant', 'customer service', 'hotelería', 'restaurante'],
        'chef': ['chef', 'cooking', 'kitchen', 'cocina', 'gastronomía'],
        'remote': ['remote', 'teletrabajo', 'work from home'],
        'junior': ['junior', 'entry level', 'sin experiencia', 'primer empleo']
    }

    words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+\b', text.lower())
    filtered_words = [word for sector in sector_keywords.values() for word in words if word in sector]
    return list(set(filtered_words))[:15]

def detect_language(text):
    spanish_keywords = ['y', 'de', 'el', 'la', 'en', 'que', 'es', 'un', 'con', 'por']
    english_keywords = ['and', 'of', 'the', 'in', 'to', 'is', 'for', 'on', 'with', 'at']

    text_lower = text.lower()
    spanish_count = sum(word in text_lower for word in spanish_keywords)
    english_count = sum(word in text_lower for word in english_keywords)

    return 'es' if spanish_count > english_count else 'en'