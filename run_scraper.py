#!/usr/bin/env python3
"""Script para ejecutar el JobScraper y obtener ofertas freelance/bounties."""
import sys
import json
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import JobScraper

class MockApp:
    config = {
        'JOBSPY_SITES': ['indeed', 'linkedin', 'google', 'zip_recruiter'],
        'JOBSPY_COUNTRY': 'USA',
        'JOBSPY_RESULTS_WANTED': 25,
        'JOBSPY_HOURS_OLD': 168,
        'SCRAPING_TIMEOUT': 30,
        'MAX_RETRIES': 3,
    }

scraper = JobScraper(MockApp())

# Search for freelance/contract/bounty/dev jobs
search_terms = ['freelance developer', 'blockchain developer', 'AI engineer', 'smart contract', 'bounty developer']

all_jobs = []
for term in search_terms:
    print(f"Searching: {term}")
    jobs = scraper.get_jobs(search_term=term, location='remote')
    if jobs:
        for j in jobs:
            j['search_term'] = term
        all_jobs.extend(jobs)
    print(f"  Found {len(jobs) if jobs else 0} jobs")

# Deduplicate by URL
seen = set()
unique_jobs = []
for j in all_jobs:
    url = j.get('url', '')
    if url and url not in seen:
        seen.add(url)
        unique_jobs.append(j)

print(f"\nTotal unique jobs: {len(unique_jobs)}")
print(json.dumps(unique_jobs[:30], indent=2, default=str))
