import yaml
import os

def load_config():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir,  'config.yaml')
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file)

config = load_config()

GITHUB_TOKEN = config['github']['token']
SONARQUBE_URL = config['sonarqube']['url']
SONARQUBE_TOKEN = config['sonarqube']['token']
TEMPLATE_OWNER = config['github']['template_owner']
TEMPLATE_REPO = config['github']['template_repo']
TEAM_SUFFIXES = config.get('team_suffixes', ['pull', 'triage', 'push', 'maintain', 'admin'])

GITHUB_CA_CERT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), config['certificates']['github'])
SONAR_CA_CERT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), config['certificates']['sonarqube'])

if not os.path.exists(GITHUB_CA_CERT_PATH) or not os.path.exists(SONAR_CA_CERT_PATH):
    raise FileNotFoundError("Certificate files not found. Please ensure both certificate files specified in the config are in the same directory as this script.")