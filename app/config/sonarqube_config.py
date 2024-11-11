import os
import ssl
from .config import config

# SonarQube API Base URL
SONARQUBE_API_BASE_URL = config.SONARQUBE_URL

# Certificate path
SONAR_CA_CERT_PATH = config.SONAR_CA_CERT_PATH

def create_sonar_ssl_context():
    """Create SSL context for GitHub API calls"""
    return ssl.create_default_context(cafile=SONAR_CA_CERT_PATH)
SONAR_SSL_CONTEXT = create_sonar_ssl_context()

# SonarQube API Headers
SONARQUBE_DEFAULT_HEADERS = {
    "Authorization": f"Bearer {config.SONARQUBE_TOKEN}"
}

# Export configuration
__all__ = [
    'SONARQUBE_API_BASE_URL',
    'SONARQUBE_DEFAULT_HEADERS',
    'SONAR_SSL_CONTEXT'
]