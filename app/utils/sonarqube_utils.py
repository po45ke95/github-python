import asyncio
import aiohttp
import logging
from typing import List, Dict
from config.sonarqube_config import SONARQUBE_API_BASE_URL, SONARQUBE_DEFAULT_HEADERS, SONAR_SSL_CONTEXT

logger = logging.getLogger(__name__)

async def create_sonarqube_project(session: aiohttp.ClientSession, project_name: str) -> Dict:
    """Create a single SonarQube project and return project details"""
    url = f"{SONARQUBE_API_BASE_URL}/api/projects/create"
    project_key = project_name.lower().replace(" ", "-")
    data = {
        "name": project_name,
        "project": project_key
    }
    
    try:
        async with session.post(url, headers=SONARQUBE_DEFAULT_HEADERS, data=data, ssl=SONAR_SSL_CONTEXT) as response:
            if response.status == 200:
                return {"key": project_key, "name": project_name, "success": True}
            else:
                error_text = await response.text()
                logger.error(f"Failed to create SonarQube project {project_name}. Status: {response.status}, Error: {error_text}")
                return {"key": None, "name": project_name, "success": False, "error": error_text}
    except Exception as e:
        logger.error(f"Exception creating SonarQube project {project_name}: {str(e)}")
        return {"key": None, "name": project_name, "success": False, "error": str(e)}

async def create_sonarqube_projects(project_names: List[str]) -> List[Dict]:
    """Create multiple SonarQube projects concurrently"""
    async with aiohttp.ClientSession() as session:
        tasks = [
            create_sonarqube_project(session, project_name)
            for project_name in project_names
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processed_results = []
            
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append({
                        "key": None,
                        "name": "unknown",
                        "success": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
        except Exception as e:
            logger.error(f"Error in create_sonarqube_projects: {str(e)}")
            return [{"key": None, "name": name, "success": False, "error": str(e)} 
                    for name in project_names]

async def generate_sonarqube_token(session: aiohttp.ClientSession, project_key: str) -> Dict:
    """Generate a SonarQube token for a project"""
    url = f"{SONARQUBE_API_BASE_URL}/api/user_tokens/generate"
    token_name = f"{project_key}_analysis_token"
    data = {
        "name": token_name,
        "type": "PROJECT_ANALYSIS_TOKEN",
        "projectKey": project_key
    }
    
    try:
        async with session.post(url, headers=SONARQUBE_DEFAULT_HEADERS, data=data, ssl=SONAR_SSL_CONTEXT) as response:
            if response.status == 200:
                response_json = await response.json()
                return {
                    "project_key": project_key,
                    "token": response_json.get('token'),
                    "success": True
                }
            else:
                error_text = await response.text()
                return {
                    "project_key": project_key,
                    "token": None,
                    "success": False,
                    "error": error_text
                }
    except Exception as e:
        return {
            "project_key": project_key,
            "token": None,
            "success": False,
            "error": str(e)
        }

async def generate_sonarqube_tokens(project_keys: List[str]) -> List[Dict]:
    """Generate SonarQube tokens for multiple projects concurrently"""
    async with aiohttp.ClientSession() as session:
        tasks = [
            generate_sonarqube_token(session, project_key)
            for project_key in project_keys
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processed_results = []
            
            for result, project_key in zip(results, project_keys):
                if isinstance(result, Exception):
                    processed_results.append({
                        "project_key": project_key,
                        "token": None,
                        "success": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
        except Exception as e:
            logger.error(f"Error in generate_sonarqube_tokens: {str(e)}")
            return [{"project_key": key, "token": None, "success": False, "error": str(e)} 
                    for key in project_keys]

async def delete_sonarqube_project(session: aiohttp.ClientSession, project_key: str) -> bool:
    """Delete a SonarQube project"""
    url = f"{SONARQUBE_API_BASE_URL}/api/projects/delete"
    data = {
        "project": project_key
    }
    
    try:
        async with session.post(url, headers=SONARQUBE_DEFAULT_HEADERS, data=data, ssl=SONAR_SSL_CONTEXT) as response:
            if response.status == 404:
                logger.warning(f"SonarQube project '{project_key}' not found. It may have been already deleted.")
                return True
            if response.status == 200:
                logger.info(f"Successfully deleted SonarQube project: {project_key}")
                return True
            else:
                error_text = await response.text()
                logger.error(f"Failed to delete SonarQube project {project_key}. Status: {response.status}, Error: {error_text}")
                return False
    except Exception as e:
        logger.error(f"Error deleting SonarQube project {project_key}: {str(e)}")
        return False

async def delete_sonarqube_token(session: aiohttp.ClientSession, token_name: str) -> bool:
    """Delete a SonarQube token"""
    url = f"{SONARQUBE_API_BASE_URL}/api/user_tokens/revoke"
    data = {
        "name": token_name
    }
    
    try:
        async with session.post(url, headers=SONARQUBE_DEFAULT_HEADERS, data=data, ssl=SONAR_SSL_CONTEXT) as response:
            if response.status == 200:
                logger.info(f"Successfully deleted SonarQube token: {token_name}")
                return True
            else:
                error_text = await response.text()
                logger.error(f"Failed to delete SonarQube token {token_name}. Status: {response.status}, Error: {error_text}")
                return False
    except Exception as e:
        logger.error(f"Error deleting SonarQube token {token_name}: {str(e)}")
        return False

async def delete_sonarqube_tokens(session: aiohttp.ClientSession, project_key: str) -> bool:
    """Delete all tokens associated with a project"""
    try:
        url = f"{SONARQUBE_API_BASE_URL}/api/user_tokens/search"
        async with session.get(url, headers=SONARQUBE_DEFAULT_HEADERS, ssl=SONAR_SSL_CONTEXT) as response:
            if response.status != 200:
                logger.error(f"Failed to fetch tokens for project {project_key}")
                return False
            response_json = await response.json()
            tokens = response_json.get('userTokens', [])

        success = True
        for token in tokens:
            if token.get('name', '').startswith(f"{project_key}_"):
                if not await delete_sonarqube_token(session, token['name']):
                    success = False

        return success
    except Exception as e:
        logger.error(f"Error managing tokens for project {project_key}: {str(e)}")
        return False

async def delete_sonarqube_resources(org_name: str, repo_name: str) -> bool:
    """Delete all SonarQube resources associated with a repository"""
    sonar_project_key = repo_name.lower().replace(" ", "-")
    success = True

    async with aiohttp.ClientSession() as session:
        # Delete project first
        if await delete_sonarqube_project(session, sonar_project_key):
            try:
                # Then delete associated tokens
                if not await delete_sonarqube_tokens(session, sonar_project_key):
                    success = False
                    logger.warning(f"Failed to delete some SonarQube tokens for project: {sonar_project_key}")
            except Exception as e:
                logger.error(f"Error deleting SonarQube tokens: {str(e)}")
                success = False
        else:
            success = False
            logger.error(f"Failed to delete SonarQube project: {sonar_project_key}")

    return success



# Export all public functions
__all__ = [
    'create_sonarqube_project',
    'create_sonarqube_projects',
    'generate_sonarqube_token',
    'generate_sonarqube_tokens',
    'delete_sonarqube_project',
    'delete_sonarqube_tokens',
    'delete_sonarqube_resources'
]