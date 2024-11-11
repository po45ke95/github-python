from typing import Dict, List
import logging
import aiohttp
from models.response_models import TeamInfo, ProjectSummary, MultiProjectResponse
from models.project_models import (
    CreateProjectRequest, CreateMultiProjectRequest,
    UpdatedRepoPermission, PutRepoRulesetsRequest
)
from utils.github_utils import (
    create_repo, delete_repo, create_team, add_repo_to_team,
    update_secret, delete_github_team, delete_github_secret,
    update_repo_team_permission, create_repos, create_multi_repo_teams,
    update_secrets, replace_repos_topics, 
    find_org_repo_rules, org_repo_rulesets_list, update_org_repo_ruleset,
    update_team_members, remove_team_members
)
from utils.sonarqube_utils import (
    create_sonarqube_project, generate_sonarqube_token,
    delete_sonarqube_resources, create_sonarqube_projects,
    generate_sonarqube_tokens
)

logger = logging.getLogger(__name__)

class ProjectService:
    async def create_project(self, request: CreateProjectRequest) -> Dict:
        """Create a single project with GitHub repository and associated resources"""
        async with aiohttp.ClientSession() as session:
            try:
                # Create GitHub repo
                repo = await create_repo(session, request.org_name, request.repo_name)
                logger.info(f"Created GitHub repository: {repo['name']}")

                # Create or get GitHub team
                team = await create_team(session, request.org_name, request.team_name)
                logger.info(f"Using GitHub team: {team['name']}")

                # Add repo to team
                await add_repo_to_team(session, request.org_name, request.repo_name, 
                                        team['slug'], request.team_permission)
                logger.info(f"Added repository to team with {request.team_permission} permission")

                # Create SonarQube project and generate token
                sonar_project_key = await create_sonarqube_project(session, request.repo_name)
                logger.info(f"Created SonarQube project: {sonar_project_key}")

                sonar_token = await generate_sonarqube_token(session, sonar_project_key)
                logger.info("Generated SonarQube analysis token")

                # Add SonarQube token and project key to GitHub secrets
                await update_secret(session, request.org_name, request.repo_name, 
                                    "SONAR_TOKEN", sonar_token)
                await update_secret(session, request.org_name, request.repo_name, 
                                    "SONAR_PROJECT_KEY", sonar_project_key)
                logger.info("Added SonarQube token and project_key to GitHub secrets")

                return {
                    "message": "Project setup completed successfully",
                    "github_repo": repo['name'],
                    "github_team": team['name'],
                    "sonar_project_key": sonar_project_key,
                    "sonar_token": sonar_token
                }
            except Exception as e:
                logger.error(f"Error creating project: {str(e)}")
                raise

    def _format_multi_project_response(self, github_repos, github_teams, 
                                            sonar_projects, sonar_tokens) -> MultiProjectResponse:
            """Helper method to format the multi-project response"""
            projects = []
            
            for repo in github_repos:
                # Extract repo name from response
                repo_name = None
                if isinstance(repo, dict):
                    if 'name' in repo:
                        repo_name = repo['name']
                    elif 'full_name' in repo:
                        repo_name = repo['full_name'].split('/')[-1]
                
                if not repo_name:
                    logger.warning(f"Skipping repo due to missing name: {repo}")
                    continue
                    
                # Find associated teams for this repo
                repo_teams = [
                    TeamInfo(
                        name=team["name"],
                        permission=team["permission"]
                    )
                    for team in github_teams
                    if isinstance(team, dict) and 
                    "name" in team and 
                    "permission" in team and
                    team["name"] in [
                        f"{repo_name}-{perm.upper()}" 
                        for perm in ["pull", "triage", "push", "maintain", "admin"]
                    ]
                ]
                
                # Find associated SonarQube project and token
                sonar_project = next(
                    (p for p in sonar_projects 
                        if isinstance(p, dict) and 
                        p.get("success", True) and 
                        p.get("key") == repo_name),
                    None
                )
                sonar_token = next(
                    (t for t in sonar_tokens 
                        if isinstance(t, dict) and 
                        t.get("success", True) and 
                        t.get("project_key") == repo_name),
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
        async with aiohttp.ClientSession() as session:
            try:
                # Create GitHub repositories
                repos = await create_repos(session, request.org_name, 
                                            [repo.name for repo in request.repo_names])
                if not repos:
                    raise ValueError("Failed to create GitHub repositories")
                
                logger.info(f"Created GitHub repositories: {[repo.get('name') for repo in repos if isinstance(repo, dict)]}")

                # Process successful repositories
                successful_repos = []
                for repo in repos:
                    if isinstance(repo, dict):
                        if 'name' in repo:
                            successful_repos.append(repo['name'])
                        elif 'full_name' in repo:
                            successful_repos.append(repo['full_name'].split('/')[-1])

                if not successful_repos:
                    raise ValueError("No repositories were created successfully")

                # Create teams for each repository
                teams = await create_multi_repo_teams(session, request.org_name, successful_repos)
                logger.info(f"Created GitHub teams: {[team.get('name') for team in teams if isinstance(team, dict) and 'name' in team]}")

                # Set repository topics
                for repo_config in request.repo_names:
                    if repo_config.name in successful_repos and repo_config.topics:
                        topics_result = await replace_repos_topics(
                            session,
                            request.org_name, 
                            [repo_config.name], 
                            repo_config.topics
                        )
                        logger.info(f"Set topics for repository {repo_config.name}: {topics_result}")

                # Create SonarQube projects
                sonar_projects = await create_sonarqube_projects(successful_repos)
                logger.info(f"Created SonarQube projects: {[project.get('key') for project in sonar_projects if isinstance(project, dict) and project.get('success')]}")

                # Generate SonarQube tokens for successful projects
                successful_projects = [
                    project['key'] 
                    for project in sonar_projects 
                    if isinstance(project, dict) and 
                    project.get('success') and 
                    'key' in project
                ]
                sonar_tokens = await generate_sonarqube_tokens(successful_projects)
                logger.info("Generated SonarQube analysis tokens")

                # Update GitHub secrets with SonarQube information
                secrets = {}
                for project, token in zip(sonar_projects, sonar_tokens):
                    if (isinstance(project, dict) and isinstance(token, dict) and
                        project.get('success') and token.get('success')):
                        secrets["SONAR_TOKEN"] = token['token']
                        secrets["SONAR_PROJECT_KEY"] = project['key']
                
                if secrets:
                    secret_results = await update_secrets(session, request.org_name, 
                                                        successful_repos, secrets)
                    logger.info("Added SonarQube tokens and project_keys to GitHub secrets")

                # Prepare and format response
                response = self._format_multi_project_response(
                    github_repos=repos,
                    github_teams=teams,
                    sonar_projects=sonar_projects,
                    sonar_tokens=sonar_tokens
                )

                # Add topics information to the response
                for project in response.projects:
                    for repo_config in request.repo_names:
                        if project.repo_name == repo_config.name:
                            project.topics = repo_config.topics
                            break

                return response.dict()

            except Exception as e:
                logger.error(f"Error creating multi-project: {str(e)}")
                raise

    async def update_repo_permission(self, request: UpdatedRepoPermission) -> Dict:
            """Update repository team permissions"""
            async with aiohttp.ClientSession() as session:
                try:
                    team_slug = request.team_name.lower().replace(" ", "-")
                    success = await update_repo_team_permission(
                        session,
                        request.org_name,
                        request.repo_name,
                        team_slug,
                        request.new_permission
                    )
                    
                    if success:
                        return {
                            "message": f"Successfully updated {request.team_name}'s permission on {request.repo_name} to {request.new_permission}"
                        }
                    else:
                        return {
                            "message": "Failed to update repository permission"
                        }
                except Exception as e:
                    logger.error(f"Error updating repo permission: {str(e)}")
                    raise

    async def delete_project(self, org_name: str, repo_name: str) -> Dict:
        """Delete a project and all its associated resources"""
        async with aiohttp.ClientSession() as session:
            try:
                # Delete GitHub secrets first
                sonar_token_deleted = await delete_github_secret(
                    session, org_name, repo_name, "SONAR_TOKEN"
                )
                sonar_key_deleted = await delete_github_secret(
                    session, org_name, repo_name, "SONAR_PROJECT_KEY"
                )
                
                secrets_deleted = sonar_token_deleted and sonar_key_deleted
                if not secrets_deleted:
                    logger.warning(f"Some secrets for project '{repo_name}' could not be deleted")

                # Delete GitHub repo
                repo_deleted = await delete_repo(session, org_name, repo_name)
                if not repo_deleted:
                    logger.error(f"Failed to delete GitHub repository: {repo_name}")

                # Delete SonarQube resources
                sonar_deleted = await delete_sonarqube_resources(org_name, repo_name)
                if not sonar_deleted:
                    logger.error(f"Failed to delete SonarQube resources for: {repo_name}")

                if repo_deleted and sonar_deleted and secrets_deleted:
                    return {
                        "message": f"Project '{repo_name}' and related resources have been successfully deleted."
                    }
                else:
                    return {
                        "message": f"Some resources for project '{repo_name}' may not have been deleted.",
                        "details": {
                            "github_repo": repo_deleted,
                            "github_secrets": secrets_deleted,
                            "sonarqube": sonar_deleted
                        }
                    }
            except Exception as e:
                logger.error(f"Error deleting project: {str(e)}")
                raise

    async def delete_multi_project(self, org_name: str, repo_names: List[str]) -> Dict:
        """Delete multiple projects and all their associated resources"""
        async with aiohttp.ClientSession() as session:
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
                    sonar_token_deleted = await delete_github_secret(
                        session, org_name, repo_name, "SONAR_TOKEN"
                    )
                    sonar_key_deleted = await delete_github_secret(
                        session, org_name, repo_name, "SONAR_PROJECT_KEY"
                    )
                    repo_result["github_secrets"] = sonar_token_deleted and sonar_key_deleted
                    
                    # Delete team hierarchy
                    team_suffixes = ['pull', 'triage', 'push', 'maintain', 'admin']
                    teams_deleted = True
                    for suffix in team_suffixes:
                        team_name = f"{repo_name}-{suffix}"
                        team_slug = team_name.lower().replace(" ", "-")
                        if not await delete_github_team(session, org_name, team_slug):
                            teams_deleted = False
                            logger.warning(f"Failed to delete team: {team_slug}")
                    repo_result["github_teams"] = teams_deleted
                    
                    # Delete GitHub repository
                    repo_result["github_repo"] = await delete_repo(session, org_name, repo_name)
                    
                    # Delete SonarQube resources
                    repo_result["sonarqube"] = await delete_sonarqube_resources(org_name, repo_name)
                    
                except Exception as e:
                    error_message = str(e)
                    logger.error(f"Error deleting resources for repo {repo_name}: {error_message}")
                    repo_result["error"] = error_message
                
                results.append(repo_result)

            # Calculate success rate
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
                "details": results,
                "success_rate": f"{(successful_deletions / len(repo_names)) * 100:.1f}%"
            }

    async def put_repo_rulesets(self, request: PutRepoRulesetsRequest) -> Dict:
        """Update repository rulesets for multiple repositories"""
        async with aiohttp.ClientSession() as session:
            try:
                if not request.repo_names:
                    raise ValueError("Please provide at least one repository name")

                # Find the ruleset
                rule_info = await find_org_repo_rules(session, request.org_name, request.rule_name)
                if not rule_info:
                    raise ValueError(f"Repository ruleset '{request.rule_name}' not found")

                # Get current ruleset configuration
                current_ruleset = await org_repo_rulesets_list(
                    session, 
                    request.org_name, 
                    rule_info["id"]
                )
                
                # Extract current repositories
                original_repos = current_ruleset.get('conditions', {}) \
                                             .get('repository_name', {}) \
                                             .get('include', [])

                # Calculate repository changes
                updated_repos = list(set(original_repos + request.repo_names))
                added_repos = list(set(request.repo_names) - set(original_repos))

                if not updated_repos:
                    raise ValueError("No valid repository names provided")

                if not added_repos:
                    logger.info("No new repositories to add to the ruleset")
                    return {
                        "message": "No new repositories to add",
                        "original_repos": original_repos,
                        "updated_repos": updated_repos,
                        "added_repos": [],
                        "added_count": 0
                    }

                # Update the ruleset
                await update_org_repo_ruleset(
                    session, 
                    request.org_name, 
                    rule_info["id"], 
                    updated_repos
                )
                
                logger.info(f"Successfully added {len(added_repos)} repositories to ruleset {request.rule_name}")
                return {
                    "message": "Successfully updated repository rulesets",
                    "original_repos": original_repos,
                    "updated_repos": updated_repos,
                    "added_repos": added_repos,
                    "added_count": len(added_repos)
                }
                
            except ValueError as e:
                logger.error(f"Validation error in put_repo_rulesets: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Error updating repository rulesets: {str(e)}")
                raise

    async def update_team_members(self, org_name: str, teams_config: List[Dict]) -> Dict:
        """Add members to teams associated with repositories"""
        async with aiohttp.ClientSession() as session:
            try:
                results = await update_team_members(session, org_name, teams_config)
                
                # Count successes and failures
                total_updates = 0
                successful_updates = 0
                for team_result in results:
                    for member_result in team_result.get("members", []):
                        total_updates += 1
                        if member_result.get("success", False):
                            successful_updates += 1

                return {
                    "message": "Team members update completed",
                    "success_rate": f"{(successful_updates / total_updates * 100):.1f}%" if total_updates > 0 else "0%",
                    "details": {
                        "total_updates": total_updates,
                        "successful_updates": successful_updates,
                        "failed_updates": total_updates - successful_updates
                    },
                    "results": results
                }
            except Exception as e:
                logger.error(f"Error updating team members: {str(e)}")
                raise

    async def remove_team_members(self, org_name: str, teams_config: List[Dict]) -> Dict:
        """Remove members from teams associated with repositories"""
        async with aiohttp.ClientSession() as session:
            try:
                results = await remove_team_members(session, org_name, teams_config)
                
                # Count successes and failures
                total_removals = 0
                successful_removals = 0
                for team_result in results:
                    for member_result in team_result.get("members", []):
                        total_removals += 1
                        if member_result.get("success", False):
                            successful_removals += 1

                return {
                    "message": "Team members removal completed",
                    "success_rate": f"{(successful_removals / total_removals * 100):.1f}%" if total_removals > 0 else "0%",
                    "details": {
                        "total_removals": total_removals,
                        "successful_removals": successful_removals,
                        "failed_removals": total_removals - successful_removals
                    },
                    "results": results
                }
            except Exception as e:
                logger.error(f"Error removing team members: {str(e)}")
                raise

    async def __verify_ruleset_compliance(self, session: aiohttp.ClientSession,
                                        org_name: str, rule_id: int, repo_names: List[str]) -> Dict:
        """
        Private helper method to verify repository ruleset compliance
        This is an example of how we could add additional validation if needed
        """
        try:
            ruleset = await org_repo_rulesets_list(session, org_name, rule_id)
            current_repos = ruleset.get('conditions', {}) \
                                    .get('repository_name', {}) \
                                    .get('include', [])
            
            non_compliant = [
                repo for repo in repo_names 
                if repo not in current_repos
            ]
            
            return {
                "compliant": len(non_compliant) == 0,
                "non_compliant_repos": non_compliant
            }
        except Exception as e:
            logger.error(f"Error verifying ruleset compliance: {str(e)}")
            return {
                "compliant": False,
                "error": str(e)
            }

