import requests
import logging
from config import SONARQUBE_URL, SONARQUBE_TOKEN, SONAR_CA_CERT_PATH
from typing import List, Dict

logger = logging.getLogger(__name__)

def create_sonarqube_project(project_name):
    url = f"{SONARQUBE_URL}/api/projects/create"
    headers = {"Authorization": f"Bearer {SONARQUBE_TOKEN}"}
    data = {
        "name": project_name,
        "project": project_name.lower().replace(" ", "-")
    }
    
    response = requests.post(url, headers=headers, data=data, verify=SONAR_CA_CERT_PATH)
    response.raise_for_status()
    return data["project"]

def create_sonarqube_projects(project_names: List[str]) -> List[Dict]:
    created_projects = []
    for project_name in project_names:
        try:
            project_key = create_sonarqube_project(project_name)
            created_projects.append({"key": project_key, "name": project_name, "success": True})
        except Exception as e:
            logger.error(f"Failed to create SonarQube project {project_name}: {str(e)}")
            created_projects.append({"key": None, "name": project_name, "success": False, "error": str(e)})
    return created_projects

def generate_sonarqube_token(project_key):
    url = f"{SONARQUBE_URL}/api/user_tokens/generate"
    headers = {"Authorization": f"Bearer {SONARQUBE_TOKEN}"}
    token_name = f"{project_key}_analysis_token"
    data = {
        "name": token_name,
        "type": "PROJECT_ANALYSIS_TOKEN",
        "projectKey": project_key
    }
    
    response = requests.post(url, headers=headers, data=data, verify=SONAR_CA_CERT_PATH)
    response.raise_for_status()
    return response.json().get('token')

def generate_sonarqube_tokens(project_keys: List[str]) -> List[Dict]:
    generated_tokens = []
    for project_key in project_keys:
        try:
            token = generate_sonarqube_token(project_key)
            generated_tokens.append({"project_key": project_key, "token": token, "success": True})
        except Exception as e:
            logger.error(f"Failed to generate SonarQube token for project {project_key}: {str(e)}")
            generated_tokens.append({"project_key": project_key, "token": None, "success": False, "error": str(e)})
    return generated_tokens

def delete_sonarqube_project(project_key):
    url = f"{SONARQUBE_URL}/api/projects/delete"
    headers = {"Authorization": f"Bearer {SONARQUBE_TOKEN}"}
    data = {
        "project": project_key
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, verify=SONAR_CA_CERT_PATH)
        if response.status_code == 404:
            logger.warning(f"SonarQube project '{project_key}' not found. It may have been already deleted.")
            return True
        response.raise_for_status()
        logger.info(f"Successfully deleted SonarQube project: {project_key}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting SonarQube project: {e}")
        return False

def delete_sonarqube_tokens(project_key):
    url = f"{SONARQUBE_URL}/api/user_tokens/search"
    headers = {"Authorization": f"Bearer {SONARQUBE_TOKEN}"}
    
    response = requests.get(url, headers=headers, verify=SONAR_CA_CERT_PATH)
    response.raise_for_status()
    tokens = response.json().get('userTokens', [])
    
    for token in tokens:
        if token.get('name').startswith(f"{project_key}_"):
            delete_sonarqube_token(token['name'])

def delete_sonarqube_token(token_name):
    url = f"{SONARQUBE_URL}/api/user_tokens/revoke"
    headers = {"Authorization": f"Bearer {SONARQUBE_TOKEN}"}
    data = {
        "name": token_name
    }
    
    response = requests.post(url, headers=headers, data=data, verify=SONAR_CA_CERT_PATH)
    response.raise_for_status()
    logger.info(f"Successfully deleted SonarQube token: {token_name}")

def delete_sonarqube_resources(org_name, repo_name):
    sonar_project_key = repo_name.lower().replace(" ", "-")
    success = True

    if delete_sonarqube_project(sonar_project_key):
        try:
            delete_sonarqube_tokens(sonar_project_key)
            logger.info(f"Deleted SonarQube tokens for project: {sonar_project_key}")
        except Exception as e:
            logger.error(f"Error deleting SonarQube tokens: {str(e)}")
            success = False
    else:
        success = False

    return success

__all__ = ['create_sonarqube_project', 'create_sonarqube_projects', 
            'generate_sonarqube_token', 'generate_sonarqube_tokens', 
            'delete_sonarqube_project', 'delete_sonarqube_tokens', 
            'delete_sonarqube_resources']