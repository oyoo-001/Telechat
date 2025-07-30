# -*- coding: utf-8 -*-
"""
Created on Wed Jul 30 11:06:12 2025

@author: Byron Okoth
"""

# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_fallback_secret_key_for_development_only_change_this')
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB limit for uploads

    # MySQL Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'password')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'chat_app_db')

    # Email Configuration (for password recovery)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')