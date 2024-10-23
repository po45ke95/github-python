from typing import Dict, List
import logging
from models.response_models import TeamInfo, ProjectSummary, MultiProjectResponse
from models.project_models import (
    CreateProjectRequest, CreateMultiProjectRequest,
    UpdatedRepoPermission, UpdateMultiRepoPermission
)
from utils.github_utils import (
    create_repo, delete_repo, create_team, add_repo_to_team,
    update_secret, delete_github_team, delete_github_secret,
    update_repo_team_permission, update_repo_team_permissions,
    create_repos, create_multi_repo_teams, update_secrets
)
from utils.sonarqube_utils import (
    create_sonarqube_project, generate_sonarqube_token,
    delete_sonarqube_resources, create_sonarqube_projects,
    generate_sonarqube_tokens
)

logger = logging.getLogger(__name__)

class ProjectService:
    async def create_project(self, request: CreateProjectRequest) -> Dict:
        # Create GitHub repo
        repo = create_repo(request.org_name, request.repo_name)
        logger.info(f"Created GitHub repository: {repo['name']}")

        # Create or get GitHub team
        team = create_team(request.org_name, request.team_name)
        logger.info(f"Using GitHub team: {team['name']}")

        # Add repo to team
        add_repo_to_team(request.org_name, request.repo_name, team['slug'], 
                        request.team_permission)
        logger.info(f"Added repository to team with {request.team_permission} permission")

        # Create SonarQube project
        sonar_project_key = create_sonarqube_project(request.repo_name)
        logger.info(f"Created SonarQube project: {sonar_project_key}")

        # Generate SonarQube token
        sonar_token = generate_sonarqube_token(sonar_project_key)
        logger.info("Generated SonarQube analysis token")

        # Add SonarQube token and project key to GitHub secrets
        update_secret(request.org_name, request.repo_name, "SONAR_TOKEN", sonar_token)
        update_secret(request.org_name, request.repo_name, "SONAR_PROJECT_KEY", sonar_project_key)
        logger.info("Added SonarQube token and project_key to GitHub secrets")

        return {
            "message": "Project setup completed successfully",
            "github_repo": repo['name'],
            "github_team": team['name'],
            "sonar_project_key": sonar_project_key,
            "sonar_token": sonar_token
        }

    def _format_multi_project_response(self, github_repos, github_teams, sonar_projects, sonar_tokens) -> MultiProjectResponse:
        """Helper method to format the multi-project response"""
        projects = []
        
        # Group data by repository
        for repo in github_repos:
            if not repo["success"]:
                continue
                
            repo_name = repo["name"]
            
            # Find all teams for this repo using exact matching with prefix
            repo_teams = [
                TeamInfo(
                    name=team["name"],
                    permission=team["permission"]
                )
                for team in github_teams
                if team["success"] and (
                    # 精確匹配：檢查團隊名稱是否為 "repo_name-permission"
                    team["name"] in [
                        f"{repo_name}-{perm}" 
                        for perm in ["pull", "triage", "push", "maintain", "admin"]
                    ]
                )
            ]
            
            # Find sonar project and token
            sonar_project = next(
                (p for p in sonar_projects if p["success"] and p["key"] == repo_name),
                None
            )
            sonar_token = next(
                (t for t in sonar_tokens if t["success"] and t["project_key"] == repo_name),
                None
            )
            
            if sonar_project and sonar_token:
                projects.append(ProjectSummary(
                    repo_name=repo_name,
                    teams=repo_teams,
                    sonar_project_key=sonar_project["key"],
                    sonar_token=sonar_token["token"]
                ))
        
        return MultiProjectResponse(
            message="Multi-project setup completed",
            projects=projects
        )


    async def create_multi_project(self, request: CreateMultiProjectRequest) -> Dict:
        """Create multiple projects with their associated resources"""
        try:
            # Create GitHub repos
            repos = create_repos(request.org_name, request.repo_names)
            logger.info(f"Created GitHub repositories: {[repo['name'] for repo in repos if repo['success']]}")

            # Create GitHub teams
            successful_repos = [repo['name'] for repo in repos if repo['success']]
            teams = create_multi_repo_teams(request.org_name, successful_repos)
            logger.info(f"Created GitHub teams: {[team['name'] for team in teams if team['success']]}")

            # Create SonarQube projects
            sonar_projects = create_sonarqube_projects(successful_repos)
            logger.info(f"Created SonarQube projects: {[project['key'] for project in sonar_projects if project['success']]}")

            # Generate SonarQube tokens
            successful_projects = [project['key'] for project in sonar_projects if project['success']]
            sonar_tokens = generate_sonarqube_tokens(successful_projects)
            logger.info("Generated SonarQube analysis tokens")

            # Update GitHub secrets
            secrets = {}
            for project, token in zip(sonar_projects, sonar_tokens):
                if project['success'] and token['success']:
                    secrets["SONAR_TOKEN"] = token['token']
                    secrets["SONAR_PROJECT_KEY"] = project['key']
            
            secret_results = update_secrets(request.org_name, successful_repos, secrets)
            logger.info("Added SonarQube tokens and project_keys to GitHub secrets")

            # Format and return the response
            return self._format_multi_project_response(
                github_repos=repos,
                github_teams=teams,
                sonar_projects=sonar_projects,
                sonar_tokens=sonar_tokens
            ).dict()  # Convert to dict for JSON response

        except Exception as e:
            logger.error(f"Error creating multi-project: {str(e)}")
            raise


    async def update_repo_permission(self, request: UpdatedRepoPermission) -> Dict:
        team_slug = request.team_name.lower().replace(" ", "-")
        success = update_repo_team_permission(
            request.org_name,
            request.repo_name,
            team_slug,
            request.new_permission
        )
        
        return {
            "message": f"Successfully updated {request.team_name}'s permission on {request.repo_name} to {request.new_permission}"
        } if success else {
            "message": "Failed to update repository permission"
        }

    async def delete_project(self, org_name: str, repo_name: str) -> Dict:
        # Delete GitHub secrets
        delete_github_secret(org_name, repo_name, "SONAR_TOKEN")
        delete_github_secret(org_name, repo_name, "SONAR_PROJECT_KEY")

        # Delete GitHub repo and SonarQube resources
        repo_deleted = delete_repo(org_name, repo_name)
        sonar_deleted = delete_sonarqube_resources(org_name, repo_name)

        return {
            "message": f"Project '{repo_name}' and related resources have been successfully deleted."
        } if repo_deleted and sonar_deleted else {
            "message": f"Some resources for project '{repo_name}' may not have been deleted."
        }

    async def delete_multi_project(self, org_name: str, repo_names: List[str]) -> Dict:
        results = []
        
        for repo_name in repo_names:
            repo_result = {
                "repo_name": repo_name,
                "github_repo": False,
                "github_secrets": False,
                "github_teams": False,
                "sonarqube": False
            }
            
            try:
                # Delete GitHub secrets
                sonar_token_deleted = delete_github_secret(org_name, repo_name, "SONAR_TOKEN")
                sonar_key_deleted = delete_github_secret(org_name, repo_name, "SONAR_PROJECT_KEY")
                repo_result["github_secrets"] = sonar_token_deleted and sonar_key_deleted
                
                # Delete teams
                team_suffixes = ['pull', 'triage', 'push', 'maintain', 'admin']
                teams_deleted = True
                for suffix in team_suffixes:
                    team_name = f"{repo_name}-{suffix}"
                    team_slug = team_name.lower().replace(" ", "-")
                    if not delete_github_team(org_name, team_slug):
                        teams_deleted = False
                repo_result["github_teams"] = teams_deleted
                
                # Delete GitHub repo and SonarQube resources
                repo_result["github_repo"] = delete_repo(org_name, repo_name)
                repo_result["sonarqube"] = delete_sonarqube_resources(org_name, repo_name)
                
            except Exception as e:
                logger.error(f"Error deleting resources for repo {repo_name}: {str(e)}")
                repo_result["error"] = str(e)
            
            results.append(repo_result)

        successful_deletions = sum(
            1 for result in results 
            if all([
                result["github_repo"],
                result["github_secrets"],
                result["github_teams"],
                result["sonarqube"]
            ])
        )
        
        return {
            "message": f"Successfully deleted {successful_deletions}/{len(repo_names)} projects",
            "details": results
        }