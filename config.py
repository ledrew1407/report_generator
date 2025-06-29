import os

class Config:
    # Generate a strong secret key for session management and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess-this-secret-key-replace-me-in-production'
    # For a real application, consider using PostgreSQL or MySQL. SQLite is simple for demo.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False