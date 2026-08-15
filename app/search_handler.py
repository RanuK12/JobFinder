# search_handler.py

from flask import request, jsonify
from app import db
import os
from flask_sqlalchemy import SQLAlchemy

def get_job_title_matches(search_term):
    if not search_term:
        return []
    
    # Convert to lowercase for case-insensitive search
    search_term = search_term.lower()
    
    # Query using SQL LIKE operator
    from app.models import Job
    results = Job.query.filter(Job.title.ilike(f'%{search_term}%')).all()
    
    # Return list of matching job titles
    return [job.title for job in results]

@app.route('/search', methods=['GET'])
def search_jobs()
    search_term = request.args.get('q')
    matches = get_job_title_matches(search_term)
    return jsonify({'matches': matches})