import os
import ssl
from .config import config

# GitHub API Base URL and Version
GITHUB_API_BASE_URL = os.getenv('GITHUB_API_URL', 'https://api.github.com')
GITHUB_API_VERSION = os.getenv('GITHUB_API_VERSION', '2022-11-28')

# Certificate path
GITHUB_CA_CERT_PATH = config.GITHUB_CA_CERT_PATH

def create_github_ssl_context():
    """Create SSL context for GitHub API calls"""
    return ssl.create_default_context(cafile=GITHUB_CA_CERT_PATH)
GITHUB_SSL_CONTEXT = create_github_ssl_context()

# GitHub API Headers
GITHUB_DEFAULT_HEADERS = {
    "Authorization": f"token {config.GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Headers for different API versions and previews
GITHUB_HEADERS_WITH_PREVIEW = {
    **GITHUB_DEFAULT_HEADERS,
    "Accept": "application/vnd.github.baptiste-preview+json"
}

GITHUB_HEADERS_WITH_VERSION = {
    **GITHUB_DEFAULT_HEADERS,
    "X-Github-Api-Version": GITHUB_API_VERSION
}

# Export configuration
__all__ = [
    'GITHUB_API_BASE_URL',
    'GITHUB_DEFAULT_HEADERS',
    'GITHUB_HEADERS_WITH_PREVIEW',
    'GITHUB_HEADERS_WITH_VERSION',
    'GITHUB_SSL_CONTEXT'
]