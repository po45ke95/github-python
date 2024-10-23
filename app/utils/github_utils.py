import requests
import logging
from typing import List, Dict
from base64 import b64encode
from nacl import encoding, public
from config import GITHUB_TOKEN, GITHUB_CA_CERT_PATH, TEMPLATE_OWNER, TEMPLATE_REPO, TEAM_SUFFIXES

logger = logging.getLogger(__name__)

def create_repo(org_name, repo_name):
    url = f"https://api.github.com/repos/{TEMPLATE_OWNER}/{TEMPLATE_REPO}/generate"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.baptiste-preview+json"
    }
    data = {
        "owner": org_name,
        "name": repo_name,
        "private": True
    }
    
    response = requests.post(url, headers=headers, json=data, verify=GITHUB_CA_CERT_PATH)
    response.raise_for_status()
    return response.json()

def delete_repo(org_name, repo_name):
    url = f"https://api.github.com/repos/{org_name}/{repo_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.delete(url, headers=headers, verify=GITHUB_CA_CERT_PATH)
    if response.status_code == 204:
        logger.info(f"Successfully deleted GitHub repository: {repo_name}")
        return True
    elif response.status_code == 404:
        logger.warning(f"GitHub repository not found: {repo_name}. It may have been already deleted.")
        return True
    else:
        logger.error(f"Failed to delete GitHub repository: {repo_name}")
        logger.error(f"Status code: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return False

def get_team(org_name, team_name):
    url = f"https://api.github.com/orgs/{org_name}/teams/{team_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers, verify=GITHUB_CA_CERT_PATH)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        response.raise_for_status()

def create_team(org_name, team_name, privacy="closed"):
    existing_team = get_team(org_name, team_name)
    if existing_team:
        logger.info(f"Team '{team_name}' already exists. Using existing team.")
        return existing_team

    url = f"https://api.github.com/orgs/{org_name}/teams"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": team_name,
        "privacy": privacy
    }

    response = requests.post(url, headers=headers, json=data, verify=GITHUB_CA_CERT_PATH)
    if response.status_code == 422:
        logger.warning(f"Team '{team_name}' might already exist. Attempting to fetch existing team.")
        existing_team = get_team(org_name, team_name)
        if existing_team:
            return existing_team
    response.raise_for_status()
    return response.json()

def delete_github_team(org_name, team_slug):
    url = f"https://api.github.com/orgs/{org_name}/teams/{team_slug}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.delete(url, headers=headers, verify=GITHUB_CA_CERT_PATH)
    if response.status_code == 204:
        logger.info(f"Successfully deleted GitHub team: {team_slug}")
        return True
    elif response.status_code == 404:
        logger.warning(f"GitHub team not found: {team_slug}. It may have been already deleted.")
        return True
    else:
        logger.error(f"Failed to delete GitHub team: {team_slug}")
        logger.error(f"Status code: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return False

def add_repo_to_team(org_name, repo_name, team_slug, permission):
    url = f"https://api.github.com/orgs/{org_name}/teams/{team_slug}/repos/{org_name}/{repo_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "permission": permission
    }

    response = requests.put(url, headers=headers, json=data, verify=GITHUB_CA_CERT_PATH)
    response.raise_for_status()
    return True

def encrypt(public_key: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")

def update_secret(repo_owner, repo_name, secret_name, secret_value):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/public-key"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers, verify=GITHUB_CA_CERT_PATH)
    response.raise_for_status()
    public_key_data = response.json()

    encrypted_value = encrypt(public_key_data["key"], secret_value)

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}"
    data = {
        "encrypted_value": encrypted_value,
        "key_id": public_key_data["key_id"]
    }
    response = requests.put(url, headers=headers, json=data, verify=GITHUB_CA_CERT_PATH)
    response.raise_for_status()
    logger.info(f"Secret '{secret_name}' updated successfully for repo '{repo_name}'.")

def update_repo_team_permission(org_name, repo_name, team_slug, permission):
    url = f"https://api.github.com/orgs/{org_name}/teams/{team_slug}/repos/{org_name}/{repo_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "permission": permission
    }

    response = requests.put(url, headers=headers, json=data, verify=GITHUB_CA_CERT_PATH)
    response.raise_for_status()
    return True


def update_repo_team_permissions(org_name: str, repo_names: List[str], team_slugs: List[str], permission: str):
    results = []
    for repo_name in repo_names:
        for team_slug in team_slugs:
            url = f"https://api.github.com/orgs/{org_name}/teams/{team_slug}/repos/{org_name}/{repo_name}"
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "permission": permission
            }
            try:
                response = requests.put(url, headers=headers, json=data, verify=GITHUB_CA_CERT_PATH)
                response.raise_for_status()
                results.append({
                    "repo": repo_name,
                    "team": team_slug,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "repo": repo_name,
                    "team": team_slug,
                    "success": False,
                    "error": str(e)
                })
    return results


def check_org_exists(org_name):
    url = f"https://api.github.com/orgs/{org_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers, verify=GITHUB_CA_CERT_PATH)
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            logger.error(f"Organization '{org_name}' not found.")
            return False
        else:
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking organization: {str(e)}")
        return False

def delete_github_secret(repo_owner, repo_name, secret_name):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.delete(url, headers=headers, verify=GITHUB_CA_CERT_PATH)
    if response.status_code == 204:
        logger.info(f"Successfully deleted GitHub secret: {secret_name}")
        return True
    elif response.status_code == 404:
        logger.warning(f"GitHub secret not found (may have been already deleted): {secret_name}")
        return True
    else:
        logger.error(f"Failed to delete GitHub secret: {secret_name}")
        logger.error(f"Status code: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return False

# Multiple repositories can be created at once
def create_repos(org_name: str, repo_names: List[str]) -> List[Dict]:
    created_repos = []
    for repo_name in repo_names:
        try:
            repo = create_repo(org_name, repo_name)
            created_repos.append({"name": repo_name, "success": True, "data": repo})
        except Exception as e:
            logger.error(f"Failed to create repo {repo_name}: {str(e)}")
            created_repos.append({"name": repo_name, "success": False, "error": str(e)})
    return created_repos

def create_repo_teams(org_name: str, repo_name: str) -> List[Dict]:
    team_suffixes = ['pull', 'triage', 'push', 'maintain', 'admin']
    created_teams = []
    for suffix in team_suffixes:
        team_name = f"{repo_name}-{suffix}"
        try:
            team = create_team(org_name, team_name)
            add_repo_to_team(org_name, repo_name, team['slug'], suffix)
            created_teams.append({"name": team_name, "success": True, "data": team, "permission": suffix})
        except Exception as e:
            logger.error(f"Failed to create or set permission for team {team_name}: {str(e)}")
            created_teams.append({"name": team_name, "success": False, "error": str(e)})
    return created_teams

def create_multi_repo_teams(org_name: str, repo_names: List[str]) -> List[Dict]:
    all_teams = []
    for repo_name in repo_names:
        repo_teams = create_repo_teams(org_name, repo_name)
        all_teams.extend(repo_teams)
    return all_teams

def update_secrets(org_name: str, repo_names: List[str], secrets: Dict[str, str]) -> List[Dict]:
    results = []
    for repo_name in repo_names:
        repo_results = []
        for secret_name, secret_value in secrets.items():
            try:
                update_secret(org_name, repo_name, secret_name, secret_value)
                repo_results.append({"secret": secret_name, "success": True})
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to update secret {secret_name} for repo {repo_name}: {str(e)}")
                if e.response is not None:
                    logger.error(f"Response content: {e.response.content}")
                repo_results.append({"secret": secret_name, "success": False, "error": str(e)})
        results.append({"repo": repo_name, "secrets": repo_results})
    return results