import logging
import aiohttp
import asyncio
from typing import List, Dict
from base64 import b64encode
from nacl import encoding, public
from config.github_config import (
    GITHUB_API_BASE_URL,
    GITHUB_DEFAULT_HEADERS,
    GITHUB_HEADERS_WITH_PREVIEW,
    GITHUB_HEADERS_WITH_VERSION,
    GITHUB_SSL_CONTEXT
)
from config.config import config

logger = logging.getLogger(__name__)

# Basic Repository Operations
async def create_repo(session: aiohttp.ClientSession, org_name: str, repo_name: str) -> Dict:
    """Create a new repository from template"""
    url = f"{GITHUB_API_BASE_URL}/repos/{config.TEMPLATE_OWNER}/{config.TEMPLATE_REPO}/generate"
    
    data = {
        "owner": org_name,
        "name": repo_name,
        "private": True
    }
    
    async with session.post(url, 
                            headers=GITHUB_HEADERS_WITH_PREVIEW, 
                            json=data,
                            ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status not in [201, 200]:
            error_text = await response.text()
            logger.error(f"Failed to create repository: {error_text}")
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )
        return await response.json()

async def delete_repo(session: aiohttp.ClientSession, org_name: str, repo_name: str) -> bool:
    """Delete a repository"""
    url = f"{GITHUB_API_BASE_URL}/repos/{org_name}/{repo_name}"

    async with session.delete(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status == 204:
            logger.info(f"Successfully deleted GitHub repository: {repo_name}")
            return True
        elif response.status == 404:
            logger.warning(f"GitHub repository not found: {repo_name}. It may have been already deleted.")
            return True
        else:
            error_text = await response.text()
            logger.error(f"Failed to delete GitHub repository: {repo_name}")
            logger.error(f"Status code: {response.status}")
            logger.error(f"Response: {error_text}")
            return False

async def create_repos(session: aiohttp.ClientSession, org_name: str, repo_names: List[str]) -> List[Dict]:
    """Create multiple repositories concurrently"""
    tasks = [
        create_repo(session, org_name, repo_name)
        for repo_name in repo_names
    ]
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed_results = []
        
        for result, repo_name in zip(results, repo_names):
            if isinstance(result, Exception):
                logger.error(f"Failed to create repository {repo_name}: {str(result)}")
                processed_results.append({
                    "name": repo_name,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    except Exception as e:
        logger.error(f"Error in create_repos: {str(e)}")
        return []

async def check_org_exists(session: aiohttp.ClientSession, org_name: str) -> bool:
    """Check if an organization exists"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}"
    
    try:
        async with session.get(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
            if response.status == 200:
                return True
            elif response.status == 404:
                logger.error(f"Organization '{org_name}' not found.")
                return False
            else:
                error_text = await response.text()
                logger.error(f"Error checking organization: {error_text}")
                return False
    except Exception as e:
        logger.error(f"Error checking organization: {str(e)}")
        return False

# Team Operations
async def get_team(session: aiohttp.ClientSession, org_name: str, team_name: str) -> Dict:
    """Get team information by name"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/teams/{team_name}"

    async with session.get(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            return None
        else:
            error_text = await response.text()
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )

async def create_team(session: aiohttp.ClientSession, org_name: str, team_name: str, privacy: str = "closed") -> Dict:
    """Create a new team or get existing team"""
    existing_team = await get_team(session, org_name, team_name)
    if existing_team:
        logger.info(f"Team '{team_name}' already exists. Using existing team.")
        return existing_team

    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/teams"
    data = {
        "name": team_name,
        "privacy": privacy
    }

    async with session.post(url, headers=GITHUB_DEFAULT_HEADERS, json=data, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status == 422:
            logger.warning(f"Team '{team_name}' might already exist. Attempting to fetch existing team.")
            existing_team = await get_team(session, org_name, team_name)
            if existing_team:
                return existing_team
        elif response.status != 201:
            error_text = await response.text()
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )
        return await response.json()

async def delete_github_team(session: aiohttp.ClientSession, org_name: str, team_slug: str) -> bool:
    """Delete a team"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/teams/{team_slug}"

    async with session.delete(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status == 204:
            logger.info(f"Successfully deleted GitHub team: {team_slug}")
            return True
        elif response.status == 404:
            logger.warning(f"GitHub team not found: {team_slug}. It may have been already deleted.")
            return True
        else:
            error_text = await response.text()
            logger.error(f"Failed to delete GitHub team: {team_slug}")
            logger.error(f"Status code: {response.status}")
            logger.error(f"Response: {error_text}")
            return False

async def create_repo_teams(session: aiohttp.ClientSession, org_name: str, repo_name: str) -> List[Dict]:
    """Create all permission-level teams for a repository"""
    team_suffixes = ['pull', 'triage', 'push', 'maintain', 'admin']
    created_teams = []
    
    for suffix in team_suffixes:
        team_name = f"{repo_name}-{suffix.capitalize()}"
        try:
            team = await create_team(session, org_name, team_name)
            await add_repo_to_team(session, org_name, repo_name, team['slug'], suffix)
            created_teams.append({
                "name": team_name,
                "success": True,
                "data": team,
                "permission": suffix
            })
        except Exception as e:
            logger.error(f"Failed to create or set permission for team {team_name}: {str(e)}")
            created_teams.append({
                "name": team_name,
                "success": False,
                "error": str(e)
            })
    return created_teams

async def create_multi_repo_teams(session: aiohttp.ClientSession, org_name: str, 
                                repo_names: List[str]) -> List[Dict]:
    """Create teams for multiple repositories"""
    all_teams = []
    for repo_name in repo_names:
        repo_teams = await create_repo_teams(session, org_name, repo_name)
        all_teams.extend(repo_teams)
    return all_teams

# Secrets Management
def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a secret value using GitHub's public key"""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")

async def get_repo_public_key(session: aiohttp.ClientSession, repo_owner: str, repo_name: str) -> Dict:
    """Get repository's public key for secret encryption"""
    url = f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/actions/secrets/public-key"
    
    async with session.get(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status != 200:
            error_text = await response.text()
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )
        return await response.json()

async def update_secret(session: aiohttp.ClientSession, repo_owner: str, repo_name: str, 
                        secret_name: str, secret_value: str) -> bool:
    """Update or create a repository secret"""
    try:
        # Get public key for encryption
        public_key_data = await get_repo_public_key(session, repo_owner, repo_name)
        encrypted_value = encrypt(public_key_data["key"], secret_value)
        
        url = f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}"
        data = {
            "encrypted_value": encrypted_value,
            "key_id": public_key_data["key_id"]
        }

        async with session.put(url, headers=GITHUB_DEFAULT_HEADERS, json=data, ssl=GITHUB_SSL_CONTEXT) as response:
            if response.status not in [201, 204]:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    response.request_info,
                    response.history,
                    status=response.status,
                    message=error_text
                )
            logger.info(f"Secret '{secret_name}' updated successfully for repo '{repo_name}'.")
            return True
    except Exception as e:
        logger.error(f"Failed to update secret '{secret_name}' for repo '{repo_name}': {str(e)}")
        raise

async def delete_github_secret(session: aiohttp.ClientSession, repo_owner: str, 
                                repo_name: str, secret_name: str) -> bool:
    """Delete a repository secret"""
    url = f"{GITHUB_API_BASE_URL}/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}"

    async with session.delete(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status == 204:
            logger.info(f"Successfully deleted GitHub secret: {secret_name}")
            return True
        elif response.status == 404:
            logger.warning(f"GitHub secret not found (may have been already deleted): {secret_name}")
            return True
        else:
            error_text = await response.text()
            logger.error(f"Failed to delete GitHub secret: {secret_name}")
            logger.error(f"Status code: {response.status}")
            logger.error(f"Response: {error_text}")
            return False

async def update_secrets(session: aiohttp.ClientSession, org_name: str, 
                        repo_names: List[str], secrets: Dict[str, str]) -> List[Dict]:
    """Update multiple secrets for multiple repositories
    
    Args:
        session: aiohttp client session
        org_name: organization name
        repo_names: list of repository names
        secrets: dictionary of secret names and values
        
    Returns:
        List of results for each repository with status of each secret update
    """
    results = []
    
    for repo_name in repo_names:
        repo_results = []
        for secret_name, secret_value in secrets.items():
            try:
                await update_secret(session, org_name, repo_name, secret_name, secret_value)
                repo_results.append({
                    "secret": secret_name,
                    "success": True
                })
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to update secret {secret_name} for repo {repo_name}: {error_msg}")
                repo_results.append({
                    "secret": secret_name,
                    "success": False,
                    "error": error_msg
                })
        
        results.append({
            "repo": repo_name,
            "secrets": repo_results
        })
    
    return results

# Permissions Management
async def add_repo_to_team(session: aiohttp.ClientSession, org_name: str, repo_name: str, 
                            team_slug: str, permission: str) -> bool:
    """Add a repository to a team with specified permission"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/teams/{team_slug}/repos/{org_name}/{repo_name}"
    data = {
        "permission": permission
    }

    async with session.put(url, headers=GITHUB_DEFAULT_HEADERS, json=data, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status != 204:
            error_text = await response.text()
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )
        return True

async def update_repo_team_permission(session: aiohttp.ClientSession, org_name: str, 
                                    repo_name: str, team_slug: str, permission: str) -> bool:
    """Update repository team permission"""
    return await add_repo_to_team(session, org_name, repo_name, team_slug, permission)

async def update_repo_team_permissions(session: aiohttp.ClientSession, org_name: str, 
                                        repo_names: List[str], team_slugs: List[str], 
                                        permission: str) -> List[Dict]:
    """Update permissions for multiple repos and teams"""
    results = []
    for repo_name in repo_names:
        for team_slug in team_slugs:
            try:
                await add_repo_to_team(session, org_name, repo_name, team_slug, permission)
                results.append({
                    "repo": repo_name,
                    "team": team_slug,
                    "success": True
                })
            except Exception as e:
                logger.error(f"Failed to update permission for {repo_name}/{team_slug}: {str(e)}")
                results.append({
                    "repo": repo_name,
                    "team": team_slug,
                    "success": False,
                    "error": str(e)
                })
    return results

# Topics Operations
async def replace_repos_topics(session: aiohttp.ClientSession, org_name: str, 
                                repo_names: List[str], topics: List[str]) -> List[Dict]:
    """Replace topics for multiple repositories"""
    results = []
    for repo_name in repo_names:
        url = f"{GITHUB_API_BASE_URL}/repos/{org_name}/{repo_name}/topics"
        try:
            async with session.put(url, headers=GITHUB_DEFAULT_HEADERS, 
                                    json={"names": topics}, ssl=GITHUB_SSL_CONTEXT) as response:
                if response.status == 200:
                    results.append({
                        "name": repo_name,
                        "success": True,
                        "status_code": response.status,
                        "topics": topics
                    })
                    logger.info(f"Successfully updated topics for repository: {repo_name}")
                else:
                    error_text = await response.text()
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=error_text
                    )
        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to update topics for repository {repo_name}: {error_message}")
            results.append({
                "name": repo_name,
                "success": False,
                "error": error_message
            })

    return results

async def get_repo_topics(session: aiohttp.ClientSession, org_name: str, repo_name: str) -> List[str]:
    """Get topics for a repository"""
    url = f"{GITHUB_API_BASE_URL}/repos/{org_name}/{repo_name}/topics"
    
    async with session.get(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("names", [])
        else:
            error_text = await response.text()
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )

# Rulesets Operations
async def find_org_repo_rules(session: aiohttp.ClientSession, org_name: str, rule_name: str) -> Dict:
    """Find specific repository ruleset in an organization"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/rulesets"
    
    async with session.get(url, headers=GITHUB_HEADERS_WITH_VERSION, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status != 200:
            error_text = await response.text()
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )
        
        rulesets = await response.json()
        for ruleset in rulesets:
            if ruleset["name"] == rule_name:
                return {
                    "id": ruleset["id"],
                    "name": ruleset["name"]
                }
        return None

async def org_repo_rulesets_list(session: aiohttp.ClientSession, org_name: str, rule_id: int) -> Dict:
    """List repository rulesets in an organization"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/rulesets/{rule_id}"
    
    async with session.get(url, headers=GITHUB_HEADERS_WITH_VERSION, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status != 200:
            error_text = await response.text()
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )
        return await response.json()

async def update_org_repo_ruleset(session: aiohttp.ClientSession, org_name: str, 
                                rule_id: int, updated_repos: List[str]) -> Dict:
    """Update repository ruleset with new repos list"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/rulesets/{rule_id}"
    
    data = {
        "conditions": {
            "ref_name": {
                "include": ["~DEFAULT_BRANCH"],
                "exclude": []
            },
            "repository_name": {
                "include": updated_repos,
                "exclude": []
            }
        }
    }
    
    async with session.put(url, headers=GITHUB_HEADERS_WITH_VERSION, 
                            json=data, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status != 200:
            error_text = await response.text()
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=error_text
            )
        return await response.json()

# GitHub Team Members Management
async def add_team_member(session: aiohttp.ClientSession, org_name: str, 
                            team_slug: str, username: str) -> Dict:
    """Add a member to a team"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/teams/{team_slug}/memberships/{username}"
    
    async with session.put(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status in [200, 201]:
            logger.info(f"Successfully added {username} to team {team_slug}")
            return {
                "username": username,
                "success": True
            }
        else:
            error_text = await response.text()
            logger.error(f"Failed to add {username} to team {team_slug}")
            logger.error(f"Status code: {response.status}")
            logger.error(f"Response: {error_text}")
            return {
                "username": username,
                "success": False,
                "error": error_text
            }

async def remove_team_member(session: aiohttp.ClientSession, org_name: str, 
                            team_slug: str, username: str) -> Dict:
    """Remove a member from a team"""
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_name}/teams/{team_slug}/memberships/{username}"
    
    async with session.delete(url, headers=GITHUB_DEFAULT_HEADERS, ssl=GITHUB_SSL_CONTEXT) as response:
        if response.status == 204:
            logger.info(f"Successfully removed {username} from team {team_slug}")
            return {
                "username": username,
                "success": True
            }
        elif response.status == 404:
            logger.warning(f"User {username} was not a member of team {team_slug}")
            return {
                "username": username,
                "success": True,
                "warning": "User was not a member"
            }
        else:
            error_text = await response.text()
            logger.error(f"Failed to remove {username} from team {team_slug}")
            logger.error(f"Status code: {response.status}")
            logger.error(f"Response: {error_text}")
            return {
                "username": username,
                "success": False,
                "error": error_text
            }

async def update_team_members(session: aiohttp.ClientSession, org_name: str, 
                            teams_config: List[Dict]) -> List[Dict]:
    """Add multiple members to multiple teams"""
    results = []
    for team_config in teams_config:
        team_name = team_config['team_name']
        team_result = {
            "team_name": team_name,
            "members": []
        }
        
        for username in team_config.get('member', []):
            member_result = await add_team_member(session, org_name, team_name, username)
            team_result["members"].append(member_result)
            
        results.append(team_result)
    return results

async def remove_team_members(session: aiohttp.ClientSession, org_name: str, 
                            teams_config: List[Dict]) -> List[Dict]:
    """Remove multiple members from multiple teams"""
    results = []
    for team_config in teams_config:
        team_name = team_config['team_name']
        team_result = {
            "team_name": team_name,
            "members": []
        }
        
        for username in team_config.get('member', []):
            member_result = await remove_team_member(session, org_name, team_name, username)
            team_result["members"].append(member_result)
            
        results.append(team_result)
    return results


__all__ = [
    'create_repo',
    'delete_repo',
    'create_repos',
    'check_org_exists',
    'get_team',
    'create_team',
    'delete_github_team',
    'create_repo_teams',
    'create_multi_repo_teams',
    'add_repo_to_team',
    'update_repo_team_permission',
    'update_repo_team_permissions',
    'encrypt',
    'update_secret',
    'update_secrets',
    'delete_github_secret',
    'replace_repos_topics',
    'get_repo_topics',
    'find_org_repo_rules',
    'org_repo_rulesets_list',
    'update_org_repo_ruleset',
    'add_team_member',
    'remove_team_member',
    'update_team_members',
    'remove_team_members',
]