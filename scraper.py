"""
Job Scraper Module - Multi-source aggregator

Uses reliable public APIs that work on cloud platforms:
- Remotive API (remote-first jobs, no auth)
- Arbeitnow API (Europe + remote, no auth)
- RemoteOK API (tech jobs, no auth)

Falls back to JobSpy if available (Indeed/LinkedIn/Google when not blocked).
"""

import re
import logging
from typing import Dict, List, Optional
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Custom exception for scraper errors."""
    pass


class JobScraper:
    """Multi-source job scraper using public APIs."""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Accept': 'application/json, text/html;q=0.9, */*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
    }

    def __init__(self, app=None):
        self.config = app.config if app else {}
        self.logger = logging.getLogger('JobScraper')

    # =========================================================================
    # Main entry point
    # =========================================================================

    def get_jobs(
        self,
        cv_text: str = None,
        language: str = 'es',
        search_term: str = None,
        location: str = None,
        job_type: str = None,
        is_remote: bool = False,
        results_wanted: int = 30,
        hours_old: int = 168,
        country: str = None,
        **_kwargs,
    ) -> List[Dict]:
        """Search jobs across multiple sources concurrently."""
        # Determine search term
        if not search_term and cv_text:
            search_term = self._build_search_term(cv_text)
        if not search_term:
            search_term = 'developer'

        search_term = search_term.strip()
        location = (location or '').strip()

        self.logger.info(
            f"Search: term='{search_term}' location='{location}' "
            f"remote={is_remote} country='{country}'"
        )

        # Run all sources concurrently for speed
        all_jobs: List[Dict] = []
        sources = [
            ('Remotive', self._fetch_remotive),
            ('Arbeitnow', self._fetch_arbeitnow),
            ('RemoteOK', self._fetch_remoteok),
        ]

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(fn, search_term, location, is_remote): name
                for name, fn in sources
            }
            for future in as_completed(futures, timeout=25):
                source = futures[future]
                try:
                    jobs = future.result(timeout=20) or []
                    self.logger.info(f"{source}: {len(jobs)} jobs")
                    all_jobs.extend(jobs)
                except Exception as e:
                    self.logger.warning(f"{source} failed: {e}")

        # Try JobSpy as bonus source if available
        try:
            jobspy_jobs = self._try_jobspy(
                search_term, location, is_remote, job_type, country, results_wanted
            )
            if jobspy_jobs:
                self.logger.info(f"JobSpy: {len(jobspy_jobs)} jobs")
                all_jobs.extend(jobspy_jobs)
        except Exception as e:
            self.logger.debug(f"JobSpy unavailable: {e}")

        # Deduplicate by (title, company)
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = (
                (job.get('title') or '').lower().strip(),
                (job.get('company') or '').lower().strip()
            )
            if key in seen or not key[0] or not key[1]:
                continue
            seen.add(key)
            unique_jobs.append(job)

        # Filter by job_type if specified
        if job_type:
            jt_lower = job_type.lower().replace('-', '').replace(' ', '')
            unique_jobs = [
                j for j in unique_jobs
                if jt_lower in (j.get('job_type', '') or '').lower().replace('-', '').replace(' ', '')
                or not j.get('job_type')
            ]

        # Filter by remote if requested
        if is_remote:
            unique_jobs = [
                j for j in unique_jobs
                if j.get('is_remote') or 'remote' in (j.get('location', '') or '').lower()
            ]

        # Filter by location if specified (loose match)
        if location and not is_remote:
            loc_lower = location.lower()
            unique_jobs = [
                j for j in unique_jobs
                if loc_lower in (j.get('location', '') or '').lower()
                or (j.get('is_remote') and 'remote' in loc_lower)
                or not j.get('location')
            ]

        # Sort by relevance score (title matches matter most, then tags, then desc)
        query_keywords = [
            w.lower() for w in re.findall(r'\b\w+\b', search_term)
            if len(w) > 2 and w.lower() not in {'and', 'the', 'for', 'with'}
        ]

        def relevance_score(job: Dict) -> tuple:
            title = (job.get('title') or '').lower()
            tags = ' '.join((job.get('tags') or [])).lower()
            desc = (job.get('description') or '').lower()[:500]

            score = 0
            for kw in query_keywords:
                if kw in title:
                    score += 5  # title match is most important
                if kw in tags:
                    score += 2
                if kw in desc:
                    score += 1
            return (score, job.get('date_posted', ''))

        unique_jobs.sort(key=relevance_score, reverse=True)

        # If we have enough good matches, drop the irrelevant ones
        # (only keep jobs that match at least one query keyword in title or tags)
        if len(unique_jobs) > results_wanted and query_keywords:
            high_quality = []
            low_quality = []
            for job in unique_jobs:
                title = (job.get('title') or '').lower()
                tags = ' '.join((job.get('tags') or [])).lower()
                if any(kw in title or kw in tags for kw in query_keywords):
                    high_quality.append(job)
                else:
                    low_quality.append(job)
            # Only fall back to low quality if we don't have enough high quality
            if len(high_quality) >= results_wanted // 2:
                unique_jobs = high_quality + low_quality

        result = unique_jobs[:results_wanted]
        self.logger.info(f"Total: {len(result)} unique jobs returned")
        return result

    # =========================================================================
    # Source: Remotive (remote-first, very reliable)
    # =========================================================================

    def _fetch_remotive(
        self, search_term: str, location: str, is_remote: bool
    ) -> List[Dict]:
        """Fetch from Remotive API. Returns remote-only jobs."""
        try:
            url = 'https://remotive.com/api/remote-jobs'
            params = {'search': search_term, 'limit': 60}
            r = requests.get(url, params=params, headers=self.HEADERS, timeout=15)
            if r.status_code != 200:
                return []
            data = r.json()

            # Build search keywords for client-side filtering
            keywords = [
                w.lower() for w in re.findall(r'\b\w+\b', search_term)
                if len(w) > 2
            ]

            jobs = []
            for item in data.get('jobs', []):
                if not isinstance(item, dict):
                    continue
                title = item.get('title', '') or ''
                company = item.get('company_name', '') or ''
                if not title or not company:
                    continue

                description = self._clean_html(item.get('description', '') or '')
                tags = item.get('tags', []) or []

                # Client-side filter to handle Remotive's loose matching
                searchable = ' '.join([
                    title.lower(),
                    company.lower(),
                    description.lower()[:1500],
                    ' '.join(t.lower() for t in tags),
                ])
                if keywords and not any(kw in searchable for kw in keywords):
                    continue

                jobs.append({
                    'title': title,
                    'company': company,
                    'location': item.get('candidate_required_location', 'Remote') or 'Remote',
                    'description': description[:1500],
                    'url': item.get('url', '') or '',
                    'platform': 'Remotive',
                    'job_type': self._normalize_job_type(item.get('job_type', '')),
                    'salary_range': item.get('salary', '') or '',
                    'date_posted': (item.get('publication_date', '') or '')[:10],
                    'is_remote': True,
                    'tags': tags[:8],
                    'company_logo': item.get('company_logo_url', '') or
                                    item.get('company_logo', '') or '',
                })
                if len(jobs) >= 30:
                    break
            return jobs
        except Exception as e:
            self.logger.debug(f"Remotive error: {e}")
            return []

    # =========================================================================
    # Source: Arbeitnow (EU + remote, very reliable)
    # =========================================================================

    def _fetch_arbeitnow(
        self, search_term: str, location: str, is_remote: bool
    ) -> List[Dict]:
        """Fetch from Arbeitnow API. Strong on Europe + remote.

        Note: Arbeitnow's `search` query parameter is unreliable, so we
        fetch the full feed and filter client-side against title/tags/desc.
        """
        try:
            url = 'https://www.arbeitnow.com/api/job-board-api'
            r = requests.get(url, headers=self.HEADERS, timeout=15)
            if r.status_code != 200:
                return []
            data = r.json()

            # Build search keywords for client-side filtering
            keywords = [
                w.lower() for w in re.findall(r'\b\w+\b', search_term)
                if len(w) > 2
            ]

            jobs = []
            for item in data.get('data', []):
                if not isinstance(item, dict):
                    continue
                title = item.get('title', '') or ''
                company = item.get('company_name', '') or ''
                if not title or not company:
                    continue

                description = self._clean_html(item.get('description', '') or '')
                tags = item.get('tags', []) or []

                # Build searchable text
                searchable = ' '.join([
                    title.lower(),
                    company.lower(),
                    description.lower()[:1500],
                    ' '.join(t.lower() for t in tags),
                ])

                # Skip if no keyword matches
                if keywords and not any(kw in searchable for kw in keywords):
                    continue

                job_types = item.get('job_types', []) or []
                job_type = self._normalize_job_type(job_types[0] if job_types else '')

                jobs.append({
                    'title': title,
                    'company': company,
                    'location': item.get('location', 'Remote') or 'Remote',
                    'description': description[:1500],
                    'url': item.get('url', '') or '',
                    'platform': 'Arbeitnow',
                    'job_type': job_type,
                    'salary_range': '',
                    'date_posted': self._format_arbeitnow_date(item.get('created_at')),
                    'is_remote': bool(item.get('remote', False)),
                    'tags': tags[:8],
                    'company_logo': '',
                })
                if len(jobs) >= 30:
                    break
            return jobs
        except Exception as e:
            self.logger.debug(f"Arbeitnow error: {e}")
            return []

    # =========================================================================
    # Source: RemoteOK (tech, very reliable)
    # =========================================================================

    def _fetch_remoteok(
        self, search_term: str, location: str, is_remote: bool
    ) -> List[Dict]:
        """Fetch from RemoteOK API. Best for tech roles.

        Strategy: Try the most specific keyword first; if it returns few
        results, fall back to broader 'dev' tag.
        """
        try:
            keywords = [
                w.lower() for w in re.findall(r'\b\w+\b', search_term)
                if len(w) > 2 and w.lower() not in {
                    'and', 'the', 'for', 'with', 'developer', 'engineer', 'senior',
                    'junior', 'lead', 'remote', 'full', 'time', 'part', 'staff',
                    'principal'
                }
            ]
            tag = keywords[0] if keywords else 'dev'

            jobs = self._remoteok_fetch_tag(tag, search_term)

            # If too few results, try broader fallback
            if len(jobs) < 5:
                fallback_jobs = self._remoteok_fetch_tag('dev', search_term)
                # Filter fallback by query keywords
                query_kws = [w.lower() for w in re.findall(r'\b\w+\b', search_term) if len(w) > 2]
                for job in fallback_jobs:
                    text = (job['title'] + ' ' + ' '.join(job.get('tags', []))).lower()
                    if any(kw in text for kw in query_kws):
                        jobs.append(job)

            return jobs
        except Exception as e:
            self.logger.debug(f"RemoteOK error: {e}")
            return []

    def _remoteok_fetch_tag(self, tag: str, search_term: str) -> List[Dict]:
        """Fetch RemoteOK jobs for a specific tag, with client-side keyword filter."""
        try:
            url = f'https://remoteok.com/api?tag={tag}'
            r = requests.get(url, headers=self.HEADERS, timeout=15)
            if r.status_code != 200:
                return []
            data = r.json()

            keywords = [
                w.lower() for w in re.findall(r'\b\w+\b', search_term) if len(w) > 2
            ]

            jobs = []
            for item in data[1:80] if isinstance(data, list) else []:
                if not isinstance(item, dict):
                    continue
                title = item.get('position', '') or ''
                company = item.get('company', '') or ''
                if not title or not company:
                    continue

                tags = (item.get('tags', []) or [])[:8]
                description = self._clean_html(item.get('description', '') or '')

                # Loose match on title/tags/description
                searchable = ' '.join([
                    title.lower(),
                    ' '.join(t.lower() for t in tags),
                    description.lower()[:1000],
                ])
                if keywords and not any(kw in searchable for kw in keywords):
                    continue

                jobs.append({
                    'title': title,
                    'company': company,
                    'location': item.get('location', 'Remote') or 'Remote',
                    'description': description[:1500],
                    'url': item.get('apply_url') or item.get('url') or
                          f"https://remoteok.com/remote-jobs/{item.get('id', '')}",
                    'platform': 'RemoteOK',
                    'job_type': 'fulltime',
                    'salary_range': self._format_remoteok_salary(item),
                    'date_posted': (item.get('date', '') or '')[:10],
                    'is_remote': True,
                    'tags': tags,
                    'company_logo': item.get('company_logo') or item.get('logo') or '',
                })
                if len(jobs) >= 30:
                    break
            return jobs
        except Exception as e:
            self.logger.debug(f"RemoteOK tag fetch error: {e}")
            return []

    # =========================================================================
    # Source: JobSpy (optional, may be blocked on cloud)
    # =========================================================================

    def _try_jobspy(
        self, search_term: str, location: str, is_remote: bool,
        job_type: str, country: str, results_wanted: int
    ) -> List[Dict]:
        """Try JobSpy if installed. Often blocked on cloud IPs."""
        try:
            from jobspy import scrape_jobs
        except ImportError:
            return []

        try:
            params = {
                'site_name': ['google', 'indeed'],
                'search_term': search_term,
                'results_wanted': min(results_wanted, 15),
                'hours_old': 168,
                'country_indeed': country or 'USA',
            }
            if location:
                params['location'] = location
                params['google_search_term'] = f"{search_term} jobs in {location}"
            elif is_remote:
                params['is_remote'] = True
                params['google_search_term'] = f"{search_term} remote jobs"
            else:
                params['google_search_term'] = f"{search_term} jobs"

            if job_type and job_type in ('fulltime', 'parttime', 'contract', 'internship'):
                params['job_type'] = job_type

            df = scrape_jobs(**params)
            if df is None or df.empty:
                return []

            jobs = []
            for _, row in df.iterrows():
                title = str(row.get('title', '') or '')
                company = str(row.get('company', '') or '')
                if not title or not company:
                    continue
                jobs.append({
                    'title': title,
                    'company': company,
                    'location': str(row.get('location', '') or 'Not specified'),
                    'description': (str(row.get('description', '') or ''))[:1500],
                    'url': str(row.get('job_url', '') or ''),
                    'platform': str(row.get('site', 'JobSpy')).title(),
                    'job_type': self._normalize_job_type(str(row.get('job_type', '') or '')),
                    'salary_range': self._format_jobspy_salary(row),
                    'date_posted': str(row.get('date_posted', '') or '')[:10],
                    'is_remote': bool(row.get('is_remote', False)),
                    'tags': [],
                    'company_logo': str(row.get('company_logo', '') or ''),
                })
            return jobs
        except Exception as e:
            self.logger.debug(f"JobSpy error: {e}")
            return []

    # =========================================================================
    # Helpers
    # =========================================================================

    def _build_search_term(self, cv_text: str) -> str:
        """Build a search term from CV text by extracting role/skills."""
        if not cv_text:
            return 'developer'
        cv_lower = cv_text.lower()

        title_patterns = [
            r'(?:senior|sr\.?|lead|principal|staff|junior|jr\.?)\s+'
            r'(?:software|frontend|backend|fullstack|full[- ]?stack|data|devops|mobile|cloud)?\s*'
            r'(?:engineer|developer|architect|scientist|analyst|designer|manager)',
            r'(?:full[- ]?stack|front[- ]?end|back[- ]?end)\s+(?:developer|engineer)',
            r'(?:data|machine learning|ml|ai)\s+(?:scientist|engineer|analyst)',
            r'(?:devops|sre|cloud|platform)\s+engineer',
            r'(?:product|project|program)\s+manager',
            r'(?:ux|ui|graphic|web|product)\s+designer',
            r'(?:qa|test|quality)\s+(?:engineer|analyst)',
            r'(?:mobile|ios|android)\s+(?:developer|engineer)',
            r'(?:security|cyber)\s+(?:engineer|analyst|architect)',
            r'business\s+analyst',
            r'scrum\s+master',
        ]
        for pattern in title_patterns:
            match = re.search(pattern, cv_lower)
            if match:
                return ' '.join(match.group(0).split())

        # Fallback: top tech skill
        tech_skills = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular',
            'vue', 'node', 'django', 'flask', 'spring', 'go', 'rust', 'swift',
            'kotlin', 'php', 'ruby', 'aws', 'azure', 'gcp', 'docker', 'kubernetes',
        ]
        counts = Counter()
        for skill in tech_skills:
            count = len(re.findall(rf'\b{re.escape(skill)}\b', cv_lower))
            if count:
                counts[skill] = count
        if counts:
            top = counts.most_common(1)[0][0]
            return f'{top} developer'

        return 'developer'

    def _clean_html(self, text: str) -> str:
        """Strip HTML tags and clean whitespace."""
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'&#39;', "'", text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _normalize_job_type(self, raw: str) -> str:
        """Normalize various job type strings to standard values."""
        if not raw:
            return ''
        raw = raw.lower().replace('-', '').replace('_', '').replace(' ', '')
        if 'full' in raw:
            return 'fulltime'
        if 'part' in raw:
            return 'parttime'
        if 'contract' in raw or 'freelance' in raw:
            return 'contract'
        if 'intern' in raw:
            return 'internship'
        if 'temp' in raw:
            return 'temporary'
        return raw

    def _format_arbeitnow_date(self, ts) -> str:
        """Format Arbeitnow Unix timestamp to YYYY-MM-DD."""
        try:
            from datetime import datetime
            return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d')
        except Exception:
            return ''

    def _format_remoteok_salary(self, item: dict) -> str:
        """Format salary from RemoteOK API."""
        try:
            sal_min = item.get('salary_min')
            sal_max = item.get('salary_max')
            if sal_min and sal_max:
                return f"USD {int(sal_min):,} - {int(sal_max):,} / yr"
            if sal_min:
                return f"USD {int(sal_min):,}+ / yr"
            return ''
        except (ValueError, TypeError):
            return ''

    def _format_jobspy_salary(self, row) -> str:
        """Format salary from JobSpy DataFrame row."""
        try:
            sal_min = row.get('min_amount')
            sal_max = row.get('max_amount')
            interval = row.get('interval', '')
            currency = row.get('currency', 'USD')
            if sal_min and sal_max:
                return f"{currency} {int(sal_min):,} - {int(sal_max):,} / {interval}"
            if sal_min:
                return f"{currency} {int(sal_min):,}+ / {interval}"
            return ''
        except (ValueError, TypeError):
            return ''
