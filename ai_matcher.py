"""
AI Job Matching Module

Matches CV content against job listings using keyword extraction,
TF-IDF-like scoring, and skill-based relevance ranking.
"""

import re
import logging
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# Technical Skills Database
# =============================================================================

TECHNICAL_SKILLS = {
    # Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
    'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl',
    'objective-c', 'dart', 'lua', 'haskell', 'elixir', 'clojure',

    # Frontend
    'react', 'angular', 'vue', 'svelte', 'next.js', 'nuxt', 'gatsby',
    'html', 'css', 'sass', 'less', 'tailwind', 'bootstrap', 'material-ui',
    'webpack', 'vite', 'babel', 'jquery', 'redux', 'mobx', 'zustand',

    # Backend
    'node', 'express', 'django', 'flask', 'fastapi', 'spring', 'rails',
    'laravel', 'asp.net', '.net', 'gin', 'fiber', 'nestjs', 'koa',
    'graphql', 'rest', 'grpc', 'websocket', 'microservices',

    # Database
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
    'dynamodb', 'cassandra', 'neo4j', 'sqlite', 'oracle', 'mariadb',
    'firebase', 'supabase', 'prisma', 'sequelize', 'mongoose',

    # DevOps & Cloud
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible',
    'jenkins', 'github actions', 'gitlab ci', 'circleci', 'nginx', 'apache',
    'linux', 'bash', 'powershell', 'ci/cd', 'devops', 'sre',

    # Data & AI/ML
    'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'spark',
    'hadoop', 'kafka', 'airflow', 'dbt', 'tableau', 'power bi',
    'machine learning', 'deep learning', 'nlp', 'computer vision',
    'data science', 'data engineering', 'etl', 'big data',

    # Mobile
    'react native', 'flutter', 'ios', 'android', 'swiftui', 'jetpack compose',
    'xamarin', 'ionic', 'cordova', 'expo',

    # Testing
    'jest', 'pytest', 'selenium', 'cypress', 'playwright', 'junit',
    'mocha', 'chai', 'vitest', 'testing', 'tdd', 'bdd', 'qa',

    # Security
    'oauth', 'jwt', 'ssl', 'tls', 'encryption', 'authentication',
    'authorization', 'cybersecurity', 'penetration testing', 'owasp',

    # Project Management & Methodologies
    'agile', 'scrum', 'kanban', 'jira', 'confluence', 'trello',
    'git', 'github', 'gitlab', 'bitbucket',

    # Other
    'blockchain', 'web3', 'solidity', 'ethereum',
    'iot', 'embedded', 'arduino', 'raspberry pi',
    'figma', 'sketch', 'adobe xd', 'ux', 'ui',
}

# Soft skills and professional keywords
PROFESSIONAL_SKILLS = {
    'leadership', 'management', 'communication', 'teamwork', 'problem-solving',
    'analytical', 'creative', 'strategic', 'planning', 'mentoring',
    'presentation', 'negotiation', 'collaboration', 'adaptability',
    'liderazgo', 'gestión', 'comunicación', 'trabajo en equipo',
    'resolución de problemas', 'analítico', 'creativo', 'estratégico',
    'planificación', 'mentoría', 'presentación', 'negociación',
    'colaboración', 'adaptabilidad',
}

# Job role keywords for categorization
ROLE_CATEGORIES = {
    'frontend': {'frontend', 'front-end', 'react', 'angular', 'vue', 'css', 'html', 'ui'},
    'backend': {'backend', 'back-end', 'api', 'server', 'database', 'microservices'},
    'fullstack': {'fullstack', 'full-stack', 'full stack'},
    'devops': {'devops', 'sre', 'infrastructure', 'cloud', 'kubernetes', 'docker'},
    'data': {'data', 'analytics', 'machine learning', 'ai', 'ml', 'scientist'},
    'mobile': {'mobile', 'ios', 'android', 'react native', 'flutter'},
    'security': {'security', 'cybersecurity', 'infosec', 'penetration'},
    'design': {'design', 'ux', 'ui', 'figma', 'user experience'},
}


# =============================================================================
# Main Matching Function
# =============================================================================

def match_jobs(cv_text: str, jobs: List[Dict]) -> List[Dict]:
    """
    Match and rank jobs based on CV content.

    Uses keyword extraction and scoring to rank jobs by relevance.

    Args:
        cv_text: Extracted text from the user's CV.
        jobs: List of job dictionaries from the scraper.

    Returns:
        List of matched jobs sorted by relevance score, with match details.
    """
    if not cv_text or not jobs:
        return []

    try:
        # Extract CV keywords and skills
        cv_keywords = extract_keywords(cv_text)
        cv_skills = extract_skills(cv_text)
        cv_roles = _identify_roles(cv_text)

        logger.info(
            f"CV Analysis - Skills: {len(cv_skills)}, "
            f"Keywords: {len(cv_keywords)}, Roles: {cv_roles}"
        )

        matched_jobs = []

        for job in jobs:
            score, match_details = _score_job(
                job, cv_skills, cv_keywords, cv_roles
            )

            if score > 0:
                matched_jobs.append({
                    **job,
                    'match_score': round(score, 2),
                    'keywords_matched': match_details.get('matched_skills', []),
                    'match_reasons': match_details.get('reasons', []),
                    'relevance': _get_relevance_label(score)
                })

        # Sort by match score (highest first)
        matched_jobs.sort(key=lambda x: x['match_score'], reverse=True)

        logger.info(f"Matched {len(matched_jobs)} jobs out of {len(jobs)} total")
        return matched_jobs

    except Exception as e:
        logger.error(f"Error in job matching: {str(e)}")
        return jobs  # Return unranked jobs as fallback


def _score_job(
    job: Dict,
    cv_skills: Set[str],
    cv_keywords: List[str],
    cv_roles: Set[str]
) -> Tuple[float, Dict]:
    """
    Calculate a relevance score for a job.

    Scoring breakdown:
    - Skill matches: up to 60 points
    - Role alignment: up to 20 points
    - Keyword overlap: up to 20 points

    Args:
        job: Job dictionary.
        cv_skills: Set of skills extracted from CV.
        cv_keywords: List of keywords from CV.
        cv_roles: Set of identified role categories.

    Returns:
        Tuple of (score, match_details_dict).
    """
    score = 0.0
    matched_skills = []
    reasons = []

    # Build job text from available fields
    job_text = ' '.join([
        job.get('title', ''),
        job.get('company', ''),
        job.get('location', ''),
        job.get('description', ''),
        ' '.join(job.get('tags', []))
    ]).lower()

    # 1. Skill matching (60% weight)
    job_skills = extract_skills(job_text)
    common_skills = cv_skills.intersection(job_skills)

    if common_skills:
        skill_score = min(len(common_skills) / max(len(cv_skills), 1) * 60, 60)
        score += skill_score
        matched_skills = list(common_skills)[:10]  # Top 10 matches
        reasons.append(
            f"Habilidades coincidentes: {', '.join(matched_skills[:5])}"
        )

    # 2. Role alignment (20% weight)
    job_roles = _identify_roles(job_text)
    common_roles = cv_roles.intersection(job_roles)

    if common_roles:
        role_score = min(len(common_roles) / max(len(cv_roles), 1) * 20, 20)
        score += role_score
        reasons.append(
            f"Rol compatible: {', '.join(common_roles)}"
        )

    # 3. Keyword overlap (20% weight)
    cv_keyword_set = set(cv_keywords)
    job_words = set(re.findall(r'\b\w+\b', job_text))
    keyword_overlap = cv_keyword_set.intersection(job_words)

    if keyword_overlap:
        keyword_score = min(
            len(keyword_overlap) / max(len(cv_keyword_set), 1) * 20, 20
        )
        score += keyword_score

    match_details = {
        'matched_skills': matched_skills,
        'reasons': reasons,
        'skill_count': len(common_skills),
        'role_alignment': list(common_roles)
    }

    return score, match_details


# =============================================================================
# Keyword & Skill Extraction
# =============================================================================

def extract_keywords(text: str) -> List[str]:
    """
    Extract relevant keywords from text.

    Filters out common stop words and short words,
    returns the most frequently occurring terms.

    Args:
        text: Input text to extract keywords from.

    Returns:
        List of top keywords (up to 20).
    """
    if not text or not isinstance(text, str):
        return []

    text = text.lower()

    # Combined stop words (English + Spanish)
    stop_words = {
        # English
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
        'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
        'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
        'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
        'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
        'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
        'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
        'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first',
        'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
        'give', 'day', 'most', 'us', 'was', 'were', 'been', 'has', 'had',
        'did', 'does', 'are', 'is', 'am', 'being',
        # Spanish
        'el', 'la', 'de', 'en', 'y', 'que', 'es', 'un', 'una', 'los',
        'las', 'del', 'con', 'por', 'para', 'se', 'al', 'lo', 'como',
        'más', 'pero', 'sus', 'le', 'ya', 'o', 'fue', 'este', 'ha',
        'si', 'porque', 'esta', 'son', 'entre', 'cuando', 'muy', 'sin',
        'sobre', 'también', 'me', 'hasta', 'hay', 'donde', 'quien',
        'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni',
        'contra', 'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto',
        'mi', 'antes', 'algunos', 'qué', 'unos', 'yo', 'otro', 'otras',
    }

    # Extract words
    words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{3,}\b', text)

    # Filter and count
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    word_counts = Counter(filtered_words)

    # Return top 20 keywords
    return [word for word, _ in word_counts.most_common(20)]


def extract_skills(text: str) -> Set[str]:
    """
    Extract technical and professional skills from text.

    Matches against a comprehensive skills database.

    Args:
        text: Input text to scan for skills.

    Returns:
        Set of identified skills.
    """
    if not text:
        return set()

    text_lower = text.lower()
    found_skills = set()

    # Check for technical skills
    for skill in TECHNICAL_SKILLS:
        # Use word boundary matching for short skills
        if len(skill) <= 3:
            if re.search(rf'\b{re.escape(skill)}\b', text_lower):
                found_skills.add(skill)
        else:
            if skill in text_lower:
                found_skills.add(skill)

    # Check for professional skills
    for skill in PROFESSIONAL_SKILLS:
        if skill in text_lower:
            found_skills.add(skill)

    return found_skills


def _identify_roles(text: str) -> Set[str]:
    """
    Identify job role categories present in text.

    Args:
        text: Text to analyze.

    Returns:
        Set of identified role categories.
    """
    text_lower = text.lower()
    identified_roles = set()

    for role, keywords in ROLE_CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            identified_roles.add(role)

    return identified_roles


def _get_relevance_label(score: float) -> str:
    """
    Convert a numeric score to a human-readable relevance label.

    Args:
        score: Numeric relevance score (0-100).

    Returns:
        Relevance label string.
    """
    if score >= 50:
        return 'high'
    elif score >= 25:
        return 'medium'
    else:
        return 'low'


# =============================================================================
# Language Detection
# =============================================================================

def detect_language(text: str) -> str:
    """
    Simple language detection based on common word frequency.

    Args:
        text: Text to analyze.

    Returns:
        Language code ('es', 'en', or 'it').
    """
    if not text:
        return 'en'

    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))

    spanish_markers = {'de', 'la', 'el', 'en', 'que', 'es', 'un', 'con', 'por', 'para'}
    english_markers = {'the', 'and', 'of', 'in', 'to', 'is', 'for', 'on', 'with', 'at'}
    italian_markers = {'di', 'il', 'la', 'che', 'è', 'per', 'sono', 'con', 'una', 'dal'}

    scores = {
        'es': len(words.intersection(spanish_markers)),
        'en': len(words.intersection(english_markers)),
        'it': len(words.intersection(italian_markers)),
    }

    return max(scores, key=scores.get)
