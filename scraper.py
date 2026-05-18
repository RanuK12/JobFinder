"""
Job Scraper Module

Scrapes job listings from multiple remote job platforms based on
keywords extracted from a user's CV. Includes rate limiting,
error handling, and anti-detection measures.
"""

import os
import re
import time
import random
import hashlib
import logging
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse, quote_plus

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import backoff

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Custom exception for scraper errors."""
    pass


class JobScraper:
    """
    Scrapes job listings from multiple platforms.

    Supports WeWorkRemotely and RemoteOK with configurable
    selectors and anti-detection measures.
    """

    def __init__(self, app):
        """
        Initialize the job scraper.

        Args:
            app: Flask application instance with config.
        """
        self.config = app.config
        self.session = requests.Session()
        self.ua = UserAgent(fallback='Mozilla/5.0')
        self.logger = logging.getLogger('JobScraper')
        self._setup_logging()

    def _setup_logging(self):
        """Configure scraper-specific logging."""
        log_dir = self.config.get('LOG_DIR', 'static/logs')
        os.makedirs(log_dir, exist_ok=True)

        if not self.logger.handlers:
            # File handler
            file_handler = logging.FileHandler(
                os.path.join(log_dir, 'scraper.log')
            )
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)

    def _get_delay(self) -> float:
        """Get a random delay between requests to avoid rate limiting."""
        delay_range = self.config.get('SCRAPING_DELAY', (2, 5))
        return random.uniform(*delay_range)

    def _get_headers(self) -> Dict[str, str]:
        """Generate realistic browser headers."""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Cache-Control': 'max-age=0',
        }

    def _validate_url(self, url: str) -> bool:
        """Validate URL format and scheme."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
        except Exception:
            return False

    def _generate_job_id(self, title: str, company: str) -> str:
        """Generate a deterministic unique job ID."""
        job_str = f"{title.lower().strip()}-{company.lower().strip()}"
        return hashlib.md5(job_str.encode()).hexdigest()[:12]

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, requests.exceptions.Timeout),
        max_tries=3,
        max_time=60
    )
    def _make_request(self, url: str) -> Optional[str]:
        """
        Make an HTTP request with retry logic.

        Args:
            url: URL to request.

        Returns:
            Response HTML content or None.
        """
        if not self._validate_url(url):
            self.logger.error(f"Invalid URL: {url}")
            return None

        time.sleep(self._get_delay())

        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=self.config.get('SCRAPING_TIMEOUT', 30),
                allow_redirects=True
            )

            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                self.logger.warning(f"Rate limited on {url}, backing off...")
                time.sleep(10)
                return None
            else:
                self.logger.warning(
                    f"HTTP {response.status_code} for {url}"
                )
                return None

        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout for {url}")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"Connection error for {url}")
            return None
        except Exception as e:
            self.logger.error(f"Request error for {url}: {str(e)}")
            return None

    def get_jobs(self, cv_text: str, language: str = 'en') -> List[Dict]:
        """
        Search for jobs based on CV text content.

        Args:
            cv_text: Extracted CV text.
            language: Preferred language code.

        Returns:
            List of job dictionaries.
        """
        self.logger.info("Starting job search")

        if not cv_text or not isinstance(cv_text, str):
            self.logger.error("Invalid CV text provided")
            return []

        cv_text = cv_text.strip()
        if not cv_text:
            self.logger.error("Empty CV text")
            return []

        # Extract search keywords
        keywords = self._extract_keywords(cv_text)
        if not keywords:
            self.logger.warning("No keywords extracted from CV")
            return []

        self.logger.info(f"Search keywords: {keywords}")

        # Search across platforms
        all_jobs = []
        seen_jobs: Set[str] = set()

        platforms = self.config.get('PLATFORMS', {})
        for platform_name, platform_config in platforms.items():
            if not platform_config.get('enabled', True):
                continue

            try:
                platform_jobs = self._scrape_platform(
                    platform_name, platform_config, keywords
                )
                for job in platform_jobs:
                    job_id = self._generate_job_id(
                        job.get('title', ''), job.get('company', '')
                    )
                    if job_id not in seen_jobs:
                        seen_jobs.add(job_id)
                        job['id'] = job_id
                        all_jobs.append(job)
            except Exception as e:
                self.logger.error(
                    f"Error scraping {platform_name}: {str(e)}"
                )
                continue

        max_jobs = self.config.get('MAX_JOBS_PER_PLATFORM', 20) * len(platforms)
        all_jobs = all_jobs[:max_jobs]

        self.logger.info(f"Found {len(all_jobs)} unique jobs")
        return all_jobs

    def _scrape_platform(
        self,
        platform_name: str,
        platform_config: Dict,
        keywords: List[str]
    ) -> List[Dict]:
        """
        Scrape jobs from a specific platform.

        Args:
            platform_name: Name of the platform.
            platform_config: Platform configuration dict.
            keywords: Search keywords.

        Returns:
            List of job dictionaries.
        """
        search_term = '+'.join(keywords[:3])
        search_url = platform_config['search_url'].format(query=quote_plus(search_term))

        self.logger.info(f"Scraping {platform_name}: {search_url}")

        html_content = self._make_request(search_url)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        jobs = []

        if platform_name == 'weworkremotely':
            jobs = self._parse_weworkremotely(soup, platform_config)
        elif platform_name == 'remoteok':
            jobs = self._parse_remoteok(soup, platform_config)

        self.logger.info(f"Found {len(jobs)} jobs on {platform_name}")
        return jobs

    def _parse_weworkremotely(
        self, soup: BeautifulSoup, config: Dict
    ) -> List[Dict]:
        """Parse WeWorkRemotely job listings."""
        jobs = []
        selectors = config.get('selectors', {})

        job_elements = soup.select(selectors.get('job_list', 'li.feature'))

        for element in job_elements[:20]:  # Limit results
            try:
                title_elem = element.select_one(selectors.get('title', 'span.title'))
                company_elem = element.select_one(selectors.get('company', 'span.company'))
                link_elem = element.select_one('a[href]')

                if not title_elem or not company_elem:
                    continue

                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True)

                url = ''
                if link_elem and link_elem.get('href'):
                    url = urljoin(config['base_url'], link_elem['href'])

                location_elem = element.select_one(
                    selectors.get('location', 'span.region')
                )
                location = location_elem.get_text(strip=True) if location_elem else 'Remote'

                if title and company:
                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': location,
                        'url': url,
                        'platform': 'WeWorkRemotely',
                        'description': '',
                        'tags': []
                    })
            except Exception as e:
                self.logger.debug(f"Error parsing WWR element: {e}")
                continue

        return jobs

    def _parse_remoteok(
        self, soup: BeautifulSoup, config: Dict
    ) -> List[Dict]:
        """Parse RemoteOK job listings."""
        jobs = []
        selectors = config.get('selectors', {})

        job_elements = soup.select(selectors.get('job_list', 'tr.job'))

        for element in job_elements[:20]:  # Limit results
            try:
                title_elem = element.select_one(
                    selectors.get('title', 'td.company_and_position h2')
                )
                company_elem = element.select_one(
                    selectors.get('company', 'td.company_and_position h3')
                )

                if not title_elem or not company_elem:
                    continue

                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True)

                # Get job URL
                url = ''
                link_elem = element.select_one('a[href*="/remote-jobs/"]')
                if link_elem and link_elem.get('href'):
                    url = urljoin(config['base_url'], link_elem['href'])

                # Get tags
                tag_elems = element.select(
                    selectors.get('tags', 'td.tags span')
                )
                tags = [t.get_text(strip=True) for t in tag_elems]

                location_elem = element.select_one(
                    selectors.get('location', 'td.location')
                )
                location = location_elem.get_text(strip=True) if location_elem else 'Remote'

                if title and company:
                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': location,
                        'url': url,
                        'platform': 'RemoteOK',
                        'description': '',
                        'tags': tags
                    })
            except Exception as e:
                self.logger.debug(f"Error parsing RemoteOK element: {e}")
                continue

        return jobs

    def _extract_keywords(self, cv_text: str) -> List[str]:
        """
        Extract relevant search keywords from CV text.

        Args:
            cv_text: CV text content.

        Returns:
            List of top keywords for job searching (max 5).
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
            'ruby', 'rails', 'go', 'rust', 'c++', 'c#', '.net', 'devops',
            'linux', 'terraform', 'jenkins', 'ci/cd', 'agile', 'scrum',
            'tensorflow', 'pytorch', 'pandas', 'data science', 'machine learning',
            'deep learning', 'redis', 'kafka', 'elasticsearch', 'blockchain',
            'mobile', 'ios', 'android', 'react native', 'flutter', 'swift',
            'kotlin', 'html', 'css', 'tailwind', 'sass', 'webpack',
            'nextjs', 'nuxt', 'svelte', 'figma', 'ux', 'ui',
        }

        # Find technical keywords in CV
        words = set(re.findall(r'\b\w+\b', cv_text))
        found_technical = [w for w in words if w in technical_keywords]

        # Also check multi-word skills
        for skill in technical_keywords:
            if ' ' in skill and skill in cv_text:
                found_technical.append(skill.replace(' ', '+'))

        if found_technical:
            # Return most common technical keywords
            from collections import Counter
            # Count occurrences in the text
            counts = Counter()
            for word in found_technical:
                counts[word] = cv_text.count(word)
            return [w for w, _ in counts.most_common(5)]

        # Fallback: use most common significant words
        stop_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
            'it', 'for', 'not', 'on', 'with', 'as', 'you', 'do', 'at',
            'this', 'but', 'by', 'from', 'or', 'an', 'will', 'my',
            'de', 'la', 'el', 'en', 'y', 'que', 'es', 'un', 'con', 'por',
        }

        all_words = re.findall(r'\b[a-z]{4,}\b', cv_text)
        filtered = [w for w in all_words if w not in stop_words]
        word_freq = Counter(filtered)

        return [w for w, _ in word_freq.most_common(5)]
