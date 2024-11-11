import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

def get_env_list(env_name: str, default: List[str] = None) -> List[str]:
    """Get a list of values from an environment variable"""
    value = os.getenv(env_name)
    if value:
        return [item.strip() for item in value.split(',')]
    return default or []

def get_cert_path(cert_name: str) -> str:
    """Get the full path of a certificate file"""
    current_dir = Path(__file__).parent
    cert_path = current_dir / cert_name
    return str(cert_path)

# Base Config Class
class Config:
    # GitHub configurations
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    TEMPLATE_OWNER = os.getenv('GITHUB_TEMPLATE_OWNER', 'Acer-Sandbox')
    TEMPLATE_REPO = os.getenv('GITHUB_TEMPLATE_REPO', 'repo-template')
    TEAM_SUFFIXES = get_env_list('TEAM_SUFFIXES', ['pull', 'triage', 'push', 'maintain', 'admin'])

    # Certificate paths configurations
    GITHUB_CA_CERT_PATH = get_cert_path(os.getenv('GITHUB_CA_CERT_PATH', 'AcerRootCA2.crt'))
    SONAR_CA_CERT_PATH = get_cert_path(os.getenv('SONAR_CA_CERT_PATH', 'sonarCA.crt'))

    # Sonarqube configurations
    SONARQUBE_URL = os.getenv('SONARQUBE_URL', 'https://sonar.intra.acer.com/sonarqube')
    SONARQUBE_TOKEN = os.getenv('SONARQUBE_TOKEN')

    def __init__(self):
        # Certificates validation check
        if not os.path.exists(self.GITHUB_CA_CERT_PATH) or not os.path.exists(self.SONAR_CA_CERT_PATH):
            raise FileNotFoundError("Certificate files not found. Please ensure both certificate files are in the config directory.")

# Create an instance of the Config class
config = Config()