"""
Test script for the job scraper
"""

import json
import logging
from scraper import JobScraper
from config import DevelopmentConfig

def test_scraper():
    """Test the job scraper with a sample CV text"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('test_scraper.log'),
            logging.StreamHandler()
        ]
    )
    
    # Sample CV text for testing
    cv_text = """
    Experienced Python developer with 5 years of experience in web development.
    Proficient in Django, Flask, and FastAPI. Strong knowledge of JavaScript,
    React, and Node.js. Experience with AWS, Docker, and Kubernetes.
    Looking for remote opportunities.
    """
    
    try:
        # Initialize scraper with development config
        scraper = JobScraper(DevelopmentConfig)
        
        # Get jobs
        jobs = scraper.get_jobs(cv_text, language='en')
        
        # Save results to file
        with open('test_results.json', 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
            
        print(f"\nFound {len(jobs)} jobs")
        if jobs:
            print("\nSample job:")
            print(json.dumps(jobs[0], indent=2, ensure_ascii=False))
            
    except Exception as e:
        logging.error(f"Error during testing: {str(e)}", exc_info=True)

if __name__ == '__main__':
    test_scraper() 