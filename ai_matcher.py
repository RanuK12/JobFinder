"""
AI Job Matching Module - Intelligent Scoring System

Inspired by career-ops (A-F grading) and job-ops (0-100 scoring).
Evaluates jobs against CV using weighted dimensions:
- Technical Skills Match (35%)
- Experience Level Alignment (20%)
- Role Category Fit (20%)
- Description Relevance (15%)
- Location/Remote Compatibility (10%)

Returns scored and graded results with detailed match breakdown.
"""

import re
import logging
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# Skills Database
# =============================================================================

TECHNICAL_SKILLS = {
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
    'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'dart',
    'react', 'angular', 'vue', 'svelte', 'nextjs', 'nuxt', 'gatsby',
    'html', 'css', 'sass', 'less', 'tailwind', 'bootstrap', 'material-ui',
    'webpack', 'vite', 'babel', 'jquery', 'redux', 'mobx', 'zustand',
    'node', 'express', 'django', 'flask', 'fastapi', 'spring', 'rails',
    'laravel', 'asp.net', '.net', 'nestjs', 'koa', 'gin', 'fiber',
    'graphql', 'rest', 'grpc', 'websocket', 'microservices',
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
    'dynamodb', 'cassandra', 'neo4j', 'sqlite', 'oracle', 'firebase',
    'supabase', 'prisma', 'sequelize', 'mongoose',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible',
    'jenkins', 'github actions', 'gitlab ci', 'circleci', 'nginx',
    'linux', 'bash', 'powershell', 'devops', 'sre',
    'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'spark',
    'hadoop', 'kafka', 'airflow', 'dbt', 'tableau', 'power bi',
    'machine learning', 'deep learning', 'nlp', 'computer vision',
    'data science', 'data engineering', 'etl', 'big data',
    'react native', 'flutter', 'ios', 'android', 'swiftui',
    'jest', 'pytest', 'selenium', 'cypress', 'playwright', 'junit',
    'oauth', 'jwt', 'ssl', 'encryption', 'cybersecurity',
    'agile', 'scrum', 'kanban', 'jira', 'git', 'github', 'gitlab',
    'figma', 'sketch', 'adobe xd', 'ux', 'ui',
    'blockchain', 'web3', 'solidity', 'ethereum',
    'salesforce', 'sap', 'erp', 'crm',
}

EXPERIENCE_INDICATORS = {
    'senior': 4, 'sr': 4, 'lead': 5, 'principal': 6, 'staff': 5,
    'architect': 6, 'director': 7, 'vp': 8, 'head': 7, 'chief': 9,
    'manager': 5, 'mid': 3, 'junior': 1, 'jr': 1, 'entry': 1,
    'intern': 0, 'associate': 2, 'experienced': 3,
}

ROLE_CATEGORIES = {
    'frontend': {'frontend', 'front-end', 'react', 'angular', 'vue', 'css', 'html', 'ui developer'},
    'backend': {'backend', 'back-end', 'api', 'server', 'database', 'microservices'},
    'fullstack': {'fullstack', 'full-stack', 'full stack'},
    'devops': {'devops', 'sre', 'infrastructure', 'cloud', 'kubernetes', 'docker', 'platform'},
    'data': {'data', 'analytics', 'machine learning', 'ai', 'ml', 'scientist', 'data engineer'},
    'mobile': {'mobile', 'ios', 'android', 'react native', 'flutter'},
    'security': {'security', 'cybersecurity', 'infosec', 'penetration'},
    'design': {'design', 'ux', 'ui', 'figma', 'user experience', 'product design'},
    'management': {'manager', 'lead', 'director', 'head of', 'vp', 'chief'},
    'qa': {'qa', 'quality', 'testing', 'test engineer', 'automation'},
}


# =============================================================================
# Main Matching Function
# =============================================================================

def match_jobs(cv_text: str, jobs: List[Dict]) -> List[Dict]:
    """
    Match and rank jobs against CV using multi-dimensional scoring.

    Scoring dimensions (total 100 points):
    - Technical Skills: 35 pts
    - Experience Level: 20 pts
    - Role Alignment: 20 pts
    - Description Relevance: 15 pts
    - Location Fit: 10 pts

    Args:
        cv_text: Extracted text from user's CV.
        jobs: List of job dictionaries from scraper.

    Returns:
        Sorted list of jobs with scores, grades, and match details.
    """
    if not cv_text or not jobs:
        return []

    try:
        # Analyze CV
        cv_profile = _analyze_cv(cv_text)
        logger.info(
            f"CV Profile - Skills: {len(cv_profile['skills'])}, "
            f"Level: {cv_profile['experience_level']}, "
            f"Roles: {cv_profile['roles']}"
        )

        matched_jobs = []
        for job in jobs:
            score_result = _score_job(job, cv_profile)
            if score_result['total_score'] > 0:
                matched_jobs.append({
                    **job,
                    'match_score': score_result['total_score'],
                    'grade': score_result['grade'],
                    'grade_color': score_result['grade_color'],
                    'relevance': score_result['relevance'],
                    'breakdown': score_result['breakdown'],
                    'matched_skills': score_result['matched_skills'],
                    'match_reasons': score_result['reasons'],
                    'experience_fit': score_result['experience_fit'],
                })

        # Sort by score descending
        matched_jobs.sort(key=lambda x: x['match_score'], reverse=True)
        logger.info(f"Matched {len(matched_jobs)}/{len(jobs)} jobs")
        return matched_jobs

    except Exception as e:
        logger.error(f"Error in job matching: {str(e)}")
        # Return jobs unranked as fallback
        for job in jobs:
            job['match_score'] = 0
            job['grade'] = '-'
            job['grade_color'] = 'gray'
            job['relevance'] = 'unknown'
        return jobs


def _analyze_cv(cv_text: str) -> Dict:
    """Extract a structured profile from CV text."""
    cv_lower = cv_text.lower()

    return {
        'skills': _extract_skills(cv_lower),
        'keywords': _extract_keywords(cv_lower),
        'experience_level': _detect_experience_level(cv_lower),
        'years_experience': _estimate_years(cv_lower),
        'roles': _identify_roles(cv_lower),
        'languages': _detect_languages_spoken(cv_lower),
        'education_level': _detect_education(cv_lower),
    }


def _score_job(job: Dict, cv_profile: Dict) -> Dict:
    """
    Calculate multi-dimensional score for a job.

    Returns dict with total_score, grade, breakdown, reasons, etc.
    """
    job_text = ' '.join([
        job.get('title', ''),
        job.get('company', ''),
        job.get('location', ''),
        job.get('description', ''),
        ' '.join(job.get('tags', [])),
        job.get('job_type', ''),
    ]).lower()

    # Dimension 1: Technical Skills (35 pts)
    skills_score, matched_skills = _score_skills(cv_profile['skills'], job_text)

    # Dimension 2: Experience Level (20 pts)
    exp_score, exp_fit = _score_experience(cv_profile['experience_level'], job_text)

    # Dimension 3: Role Alignment (20 pts)
    role_score, role_match = _score_role_alignment(cv_profile['roles'], job_text)

    # Dimension 4: Description Relevance (15 pts)
    desc_score = _score_description_relevance(cv_profile['keywords'], job_text)

    # Dimension 5: Location/Remote (10 pts)
    location_score = _score_location(job)

    # Total
    total = round(skills_score + exp_score + role_score + desc_score + location_score, 1)
    total = min(total, 100)

    # Grade assignment
    grade, grade_color = _assign_grade(total)

    # Build reasons
    reasons = []
    if matched_skills:
        reasons.append(f"Skills: {', '.join(list(matched_skills)[:5])}")
    if role_match:
        reasons.append(f"Role fit: {', '.join(role_match)}")
    if exp_fit:
        reasons.append(exp_fit)

    return {
        'total_score': total,
        'grade': grade,
        'grade_color': grade_color,
        'relevance': _get_relevance(total),
        'breakdown': {
            'skills': round(skills_score, 1),
            'experience': round(exp_score, 1),
            'role': round(role_score, 1),
            'description': round(desc_score, 1),
            'location': round(location_score, 1),
        },
        'matched_skills': list(matched_skills)[:10],
        'reasons': reasons,
        'experience_fit': exp_fit,
    }


# =============================================================================
# Scoring Functions
# =============================================================================

def _score_skills(cv_skills: Set[str], job_text: str) -> Tuple[float, Set[str]]:
    """Score technical skills match (max 35 pts)."""
    job_skills = _extract_skills(job_text)
    if not cv_skills or not job_skills:
        # If job has no specific skills listed, give partial credit
        if not job_skills and cv_skills:
            return 15.0, set()
        return 0.0, set()

    common = cv_skills.intersection(job_skills)
    if not common:
        return 0.0, set()

    # Score based on coverage of job requirements
    coverage = len(common) / len(job_skills)
    score = min(coverage * 35, 35)

    # Bonus for having many matching skills
    if len(common) >= 5:
        score = min(score + 5, 35)

    return score, common


def _score_experience(cv_level: int, job_text: str) -> Tuple[float, str]:
    """Score experience level alignment (max 20 pts)."""
    job_level = _detect_experience_level(job_text)

    if job_level == 0 and cv_level == 0:
        return 15.0, "Entry level match"

    if job_level == 0:
        return 10.0, ""  # Job doesn't specify level

    diff = abs(cv_level - job_level)
    if diff == 0:
        return 20.0, "Perfect level match"
    elif diff == 1:
        if cv_level > job_level:
            return 16.0, "Slightly overqualified"
        return 14.0, "Slight stretch role"
    elif diff == 2:
        if cv_level > job_level:
            return 10.0, "Overqualified"
        return 8.0, "Growth opportunity"
    else:
        if cv_level > job_level:
            return 5.0, "Significantly overqualified"
        return 3.0, "Significant experience gap"


def _score_role_alignment(cv_roles: Set[str], job_text: str) -> Tuple[float, List[str]]:
    """Score role category alignment (max 20 pts)."""
    job_roles = _identify_roles(job_text)

    if not cv_roles or not job_roles:
        return 10.0, []  # Neutral if can't determine

    common = cv_roles.intersection(job_roles)
    if common:
        score = min(len(common) / max(len(job_roles), 1) * 20, 20)
        return max(score, 12.0), list(common)

    # Adjacent roles get partial credit
    adjacent = {
        'frontend': {'fullstack', 'design'},
        'backend': {'fullstack', 'devops', 'data'},
        'fullstack': {'frontend', 'backend'},
        'devops': {'backend', 'security'},
        'data': {'backend', 'devops'},
        'mobile': {'frontend', 'fullstack'},
    }
    for cv_role in cv_roles:
        adj = adjacent.get(cv_role, set())
        if adj.intersection(job_roles):
            return 8.0, [f"{cv_role} (adjacent)"]

    return 3.0, []


def _score_description_relevance(cv_keywords: List[str], job_text: str) -> float:
    """Score keyword overlap with job description (max 15 pts)."""
    if not cv_keywords or not job_text:
        return 5.0

    job_words = set(re.findall(r'\b\w+\b', job_text))
    cv_keyword_set = set(cv_keywords[:20])
    overlap = cv_keyword_set.intersection(job_words)

    if not overlap:
        return 2.0

    coverage = len(overlap) / len(cv_keyword_set)
    return min(coverage * 15, 15)


def _score_location(job: Dict) -> float:
    """Score location compatibility (max 10 pts)."""
    if job.get('is_remote'):
        return 10.0  # Remote = always accessible

    location = (job.get('location', '') or '').lower()
    if 'remote' in location or 'anywhere' in location or 'worldwide' in location:
        return 10.0
    if 'hybrid' in location:
        return 7.0
    if location and location != 'not specified':
        return 5.0  # Has a location, neutral score
    return 5.0


# =============================================================================
# Grading System
# =============================================================================

def _assign_grade(score: float) -> Tuple[str, str]:
    """Assign letter grade and color based on score."""
    if score >= 80:
        return 'A', 'green'
    elif score >= 65:
        return 'B', 'blue'
    elif score >= 50:
        return 'C', 'yellow'
    elif score >= 35:
        return 'D', 'orange'
    elif score >= 20:
        return 'E', 'red'
    else:
        return 'F', 'gray'


def _get_relevance(score: float) -> str:
    """Get relevance label from score."""
    if score >= 70:
        return 'high'
    elif score >= 45:
        return 'medium'
    else:
        return 'low'


# =============================================================================
# Extraction Utilities
# =============================================================================

def _extract_skills(text: str) -> Set[str]:
    """Extract technical skills from text."""
    if not text:
        return set()
    found = set()
    for skill in TECHNICAL_SKILLS:
        if len(skill) <= 3:
            if re.search(rf'\b{re.escape(skill)}\b', text):
                found.add(skill)
        else:
            if skill in text:
                found.add(skill)
    return found


def _extract_keywords(text: str) -> List[str]:
    """Extract significant keywords from text."""
    if not text:
        return []

    stop_words = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
        'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
        'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
        'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time',
        'work', 'experience', 'company', 'team', 'project', 'role',
        'de', 'la', 'el', 'en', 'y', 'que', 'es', 'un', 'una', 'los',
        'las', 'del', 'con', 'por', 'para', 'se', 'al', 'como',
    }

    words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
    filtered = [w.lower() for w in words if w.lower() not in stop_words]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(25)]


def _detect_experience_level(text: str) -> int:
    """Detect seniority level (0-9 scale)."""
    max_level = 0
    for indicator, level in EXPERIENCE_INDICATORS.items():
        if re.search(rf'\b{re.escape(indicator)}\b', text):
            max_level = max(max_level, level)
    return max_level


def _estimate_years(text: str) -> int:
    """Estimate years of experience from CV text."""
    patterns = [
        r'(\d+)\+?\s*(?:years?|años?)\s*(?:of\s+)?(?:experience|experiencia)',
        r'(?:experience|experiencia)\s*:?\s*(\d+)\+?\s*(?:years?|años?)',
    ]
    max_years = 0
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            try:
                max_years = max(max_years, int(m))
            except ValueError:
                pass
    return max_years


def _identify_roles(text: str) -> Set[str]:
    """Identify job role categories in text."""
    found = set()
    for role, keywords in ROLE_CATEGORIES.items():
        if any(kw in text for kw in keywords):
            found.add(role)
    return found


def _detect_languages_spoken(text: str) -> List[str]:
    """Detect spoken languages mentioned in CV."""
    language_patterns = {
        'english': r'\benglish\b|\binglés\b',
        'spanish': r'\bspanish\b|\bespañol\b|\bcastellano\b',
        'french': r'\bfrench\b|\bfrancés\b',
        'german': r'\bgerman\b|\balemán\b',
        'italian': r'\bitalian\b|\bitaliano\b',
        'portuguese': r'\bportuguese\b|\bportugués\b',
        'chinese': r'\bchinese\b|\bmandarín\b|\bmandarin\b',
    }
    found = []
    for lang, pattern in language_patterns.items():
        if re.search(pattern, text):
            found.append(lang)
    return found


def _detect_education(text: str) -> str:
    """Detect highest education level."""
    if re.search(r'\b(phd|doctorate|doctorado)\b', text):
        return 'phd'
    if re.search(r'\b(master|msc|mba|maestría|máster)\b', text):
        return 'masters'
    if re.search(r'\b(bachelor|bsc|licenciatura|ingenier[ío]a|grado)\b', text):
        return 'bachelors'
    if re.search(r'\b(bootcamp|certificate|certificado|diploma)\b', text):
        return 'certificate'
    return 'unknown'
