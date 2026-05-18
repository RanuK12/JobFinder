"""
Job Scraper Module - Powered by JobSpy

Uses the python-jobspy library to aggregate job listings from multiple
platforms (Indeed, LinkedIn, Glassdoor, Google, ZipRecruiter) based on
keywords extracted from a user's CV.
"""

import re
import logging
from typing import Dict, List, Optional, Set
from collections import Counter

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Custom exception for scraper errors."""
    pass


class JobScraper:
    """
    Scrapes job listings from multiple platforms using JobSpy.

    Supports Indeed, LinkedIn, Google, Glassdoor, and ZipRecruiter.
    """

    def __init__(self, app=None):
        """
        Initialize the job scraper.

        Args:
            app: Flask application instance with config (optional).
        """
        self.config = app.config if app else {}
        self.logger = logging.getLogger('JobScraper')

    def get_jobs(
        self,
        cv_text: str = None,
        language: str = 'es',
        search_term: str = None,
        location: str = None,
        job_type: str = None,
        is_remote: bool = False,
        results_wanted: int = 25,
        hours_old: int = 168,  # 7 days
        country: str = None,
    ) -> List[Dict]:
        """
        Search for jobs using JobSpy multi-platform aggregation.

        Args:
            cv_text: Extracted CV text (used to generate search_term if not provided).
            language: Preferred language code.
            search_term: Direct search term (overrides CV extraction).
            location: Job location filter.
            job_type: Type filter (fulltime, parttime, contract, internship).
            is_remote: Filter for remote jobs only.
            results_wanted: Number of results per platform.
            hours_old: Max age of job postings in hours.
            country: Country filter for Indeed.

        Returns:
            List of job dictionaries.
        """
        self.logger.info("Starting job search with JobSpy")

        # Determine search term
        if not search_term and cv_text:
            search_term = self._build_search_term(cv_text)

        if not search_term:
            self.logger.error("No search term available")
            return []

        self.logger.info(f"Search term: '{search_term}', Location: '{location}', Remote: {is_remote}")

        try:
            from jobspy import scrape_jobs

            # Configure sites to search
            sites = self.config.get('JOBSPY_SITES', ['indeed', 'linkedin', 'google', 'zip_recruiter'])

            # Build scrape parameters
            scrape_params = {
                'site_name': sites,
                'search_term': search_term,
                'results_wanted': results_wanted,
                'hours_old': hours_old,
                'country_indeed': country or self.config.get('JOBSPY_COUNTRY', 'USA'),
            }

            if location:
                scrape_params['location'] = location

            if is_remote:
                scrape_params['is_remote'] = True

            if job_type and job_type in ('fulltime', 'parttime', 'contract', 'internship'):
                scrape_params['job_type'] = job_type

            # Google-specific search term
            google_term = search_term
            if location:
                google_term = f"{search_term} jobs in {location}"
            elif is_remote:
                google_term = f"{search_term} remote jobs"
            scrape_params['google_search_term'] = google_term

            # Execute scrape
            self.logger.info(f"Scraping with params: sites={sites}, term='{search_term}'")
            jobs_df = scrape_jobs(**scrape_params)

            if jobs_df is None or jobs_df.empty:
                self.logger.warning("JobSpy returned no results")
                return []

            # Convert DataFrame to list of dicts
            jobs = self._dataframe_to_jobs(jobs_df)
            self.logger.info(f"Found {len(jobs)} jobs from JobSpy")
            return jobs

        except ImportError:
            self.logger.error("python-jobspy not installed. Falling back to manual scraping.")
            return self._fallback_scrape(search_term, location)
        except Exception as e:
            self.logger.error(f"JobSpy error: {str(e)}")
            # Try fallback
            return self._fallback_scrape(search_term, location)

    def _dataframe_to_jobs(self, df) -> List[Dict]:
        """Convert a JobSpy pandas DataFrame to a list of job dicts."""
        jobs = []
        for _, row in df.iterrows():
            try:
                job = {
                    'title': str(row.get('title', '')) if row.get('title') else '',
                    'company': str(row.get('company', '')) if row.get('company') else '',
                    'location': str(row.get('location', '')) if row.get('location') else 'Not specified',
                    'description': str(row.get('description', ''))[:2000] if row.get('description') else '',
                    'url': str(row.get('job_url', '')) if row.get('job_url') else '',
                    'platform': str(row.get('site', '')).title() if row.get('site') else 'Unknown',
                    'job_type': str(row.get('job_type', '')) if row.get('job_type') else '',
                    'salary_range': self._format_salary(row),
                    'date_posted': str(row.get('date_posted', '')) if row.get('date_posted') else '',
                    'is_remote': bool(row.get('is_remote', False)),
                    'tags': [],
                }

                # Only add jobs with at least title and company
                if job['title'] and job['company']:
                    jobs.append(job)
            except Exception as e:
                self.logger.debug(f"Error converting row: {e}")
                continue

        return jobs

    def _format_salary(self, row) -> str:
        """Format salary range from DataFrame row."""
        try:
            min_amount = row.get('min_amount')
            max_amount = row.get('max_amount')
            interval = row.get('interval', '')
            currency = row.get('currency', 'USD')

            if min_amount and max_amount:
                return f"{currency} {int(min_amount):,} - {int(max_amount):,} / {interval}"
            elif min_amount:
                return f"{currency} {int(min_amount):,}+ / {interval}"
            elif max_amount:
                return f"Up to {currency} {int(max_amount):,} / {interval}"
            return ''
        except (ValueError, TypeError):
            return ''

    def _build_search_term(self, cv_text: str) -> str:
        """
        Build an effective search term from CV text.

        Extracts the most relevant job title/role keywords.
        """
        if not cv_text or not isinstance(cv_text, str):
            return ''

        cv_lower = cv_text.lower().strip()

        # Try to find explicit job titles first
        title_patterns = [
            r'(?:software|senior|junior|lead|principal|staff)\s+(?:engineer|developer|architect)',
            r'(?:full[- ]?stack|front[- ]?end|back[- ]?end)\s+(?:developer|engineer)',
            r'(?:data|ml|machine learning|ai)\s+(?:scientist|engineer|analyst)',
            r'(?:devops|sre|cloud|platform)\s+engineer',
            r'(?:product|project|program)\s+manager',
            r'(?:ux|ui|graphic|web)\s+designer',
            r'(?:qa|test|quality)\s+(?:engineer|analyst|automation)',
            r'(?:mobile|ios|android)\s+(?:developer|engineer)',
            r'(?:security|cyber)\s+(?:engineer|analyst)',
            r'(?:systems?|network)\s+(?:administrator|engineer)',
            r'business\s+analyst',
            r'scrum\s+master',
            r'technical\s+(?:writer|lead)',
        ]

        for pattern in title_patterns:
            matches = re.findall(pattern, cv_lower)
            if matches:
                return matches[0].title()

        # Extract key technical skills
        keywords = self._extract_keywords(cv_text)
        if keywords:
            # Use top 2-3 keywords as search term
            return ' '.join(keywords[:3])

        return 'software developer'  # Default fallback

    def _extract_keywords(self, cv_text: str) -> List[str]:
        """
        Extract relevant search keywords from CV text.

        Returns top keywords suitable for job searching.
        """
        if isinstance(cv_text, list):
            cv_text = ' '.join(cv_text)
        elif not isinstance(cv_text, str):
            return []

        cv_text = cv_text.strip().lower()
        if not cv_text:
            return []

        # Priority technical keywords
        technical_keywords = {
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
            'express', 'django', 'flask', 'spring', 'sql', 'mysql', 'postgresql',
            'mongodb', 'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git',
            'rest', 'graphql', 'api', 'microservices', 'typescript', 'php',
            'ruby', 'rails', 'go', 'rust', 'devops', 'linux', 'terraform',
            'jenkins', 'agile', 'scrum', 'tensorflow', 'pytorch', 'pandas',
            'redis', 'kafka', 'elasticsearch', 'mobile', 'ios', 'android',
            'react native', 'flutter', 'swift', 'kotlin', 'html', 'css',
            'tailwind', 'webpack', 'nextjs', 'nuxt', 'svelte', 'figma',
            'salesforce', 'sap', 'power bi', 'tableau', 'excel', 'marketing',
            'seo', 'analytics', 'blockchain', 'solidity', 'web3',
        }

        # Find technical keywords in CV
        words = set(re.findall(r'\b\w+\b', cv_text))
        found_technical = [w for w in words if w in technical_keywords]

        # Also check multi-word skills
        for skill in ['react native', 'machine learning', 'data science',
                      'deep learning', 'power bi', 'full stack']:
            if skill in cv_text:
                found_technical.append(skill.replace(' ', '-'))

        if found_technical:
            counts = Counter()
            for word in found_technical:
                counts[word] = cv_text.count(word)
            return [w for w, _ in counts.most_common(5)]

        # Fallback
        stop_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
            'it', 'for', 'not', 'on', 'with', 'as', 'you', 'do', 'at',
            'this', 'but', 'by', 'from', 'or', 'an', 'will', 'my',
            'de', 'la', 'el', 'en', 'y', 'que', 'es', 'un', 'con', 'por',
            'work', 'experience', 'company', 'year', 'team', 'project',
        }
        all_words = re.findall(r'\b[a-z]{4,}\b', cv_text)
        filtered = [w for w in all_words if w not in stop_words]
        word_freq = Counter(filtered)
        return [w for w, _ in word_freq.most_common(5)]

    def _fallback_scrape(self, search_term: str, location: str = None) -> List[Dict]:
        """
        Fallback scraper using direct HTTP requests to RemoteOK API.

        Used when JobSpy is not available or fails.
        """
        import requests
        from fake_useragent import UserAgent

        self.logger.info(f"Fallback: Scraping RemoteOK for '{search_term}'")
        jobs = []

        try:
            ua = UserAgent(fallback='Mozilla/5.0')
            headers = {
                'User-Agent': ua.random,
                'Accept': 'application/json',
            }

            # RemoteOK has a JSON API
            url = f"https://remoteok.com/api?tag={search_term.replace(' ', '+')}"
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                # First item is metadata, skip it
                for item in data[1:30]:  # Limit to 30
                    if isinstance(item, dict) and item.get('position'):
                        job = {
                            'title': item.get('position', ''),
                            'company': item.get('company', ''),
                            'location': item.get('location', 'Remote'),
                            'description': (item.get('description', '') or '')[:1500],
                            'url': item.get('url', f"https://remoteok.com/remote-jobs/{item.get('id', '')}"),
                            'platform': 'RemoteOK',
                            'job_type': 'fulltime',
                            'salary_range': self._format_remoteok_salary(item),
                            'date_posted': item.get('date', ''),
                            'is_remote': True,
                            'tags': item.get('tags', []) or [],
                        }
                        if job['title'] and job['company']:
                            jobs.append(job)

            self.logger.info(f"Fallback found {len(jobs)} jobs")
        except Exception as e:
            self.logger.error(f"Fallback scrape error: {e}")

        return jobs

    def _format_remoteok_salary(self, item: dict) -> str:
        """Format salary from RemoteOK API response."""
        try:
            sal_min = item.get('salary_min')
            sal_max = item.get('salary_max')
            if sal_min and sal_max:
                return f"USD {int(sal_min):,} - {int(sal_max):,} / year"
            elif sal_min:
                return f"USD {int(sal_min):,}+ / year"
            return ''
        except (ValueError, TypeError):
            return ''
