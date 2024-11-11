from fastapi import APIRouter, HTTPException
from models.project_models import (
    CreateProjectRequest, DeleteProjectRequest, UpdatedRepoPermission,
    CreateMultiProjectRequest, DeleteMultiProjectRequest,
    PutRepoRulesetsRequest, PutRepoRulesetsResponse,
    TeamMember, TeamMembershipRequest
)
from services.project_service import ProjectService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
project_service = ProjectService()

# @router.post("/create_project")
# async def create_project(request: CreateProjectRequest):
#     """
#     Create a new project with GitHub repository and associated resources.
    
#     Creates:
#     - GitHub repository
#     - GitHub team with specified permissions
#     - SonarQube project and token
#     - GitHub secrets for SonarQube integration
#     """
#     try:
#         return await project_service.create_project(request)
#     except Exception as e:
#         logger.error(f"Error creating project: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/repos")
async def create_multi_project(request: CreateMultiProjectRequest):
    """
    Create multiple projects simultaneously with their associated resources.
    
    Creates for each project:
    - GitHub repository
    - GitHub teams with different permission levels
    - SonarQube projects and tokens
    - GitHub secrets for SonarQube integration
    - Repository topics if specified
    """
    try:
        return await project_service.create_multi_project(request)
    except Exception as e:
        logger.error(f"Error creating multi-project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.put("/update_repo_permission")
# async def update_repo_permission(request: UpdatedRepoPermission):
#     """
#     Update GitHub repository team permissions.
    
#     Modifies the permission level (pull, push, admin, etc.) 
#     for a specified team on a given repository.
#     """
#     try:
#         return await project_service.update_repo_permission(request)
#     except Exception as e:
#         logger.error(f"Error updating repository permission: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.delete("/delete_project")
# async def delete_project(request: DeleteProjectRequest):
#     """
#     Delete a project and all its associated resources.
    
#     Removes:
#     - GitHub repository
#     - GitHub secrets
#     - SonarQube project and token
#     """
#     try:
#         return await project_service.delete_project(request.org_name, request.repo_name)
#     except Exception as e:
#         logger.error(f"Error deleting project: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.delete("/repos")
async def delete_multi_project(request: DeleteMultiProjectRequest):
    """
    Delete multiple projects and all their associated resources.
    
    Removes for each project:
    - GitHub repository
    - GitHub teams and secrets
    - SonarQube projects and tokens
    
    Returns detailed status for each project deletion.
    """
    try:
        return await project_service.delete_multi_project(
            request.org_name,
            request.repo_names
        )
    except Exception as e:
        logger.error(f"Error in delete_multi_project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/repo_rulesets", response_model=PutRepoRulesetsResponse)
async def put_repo_rulesets(request: PutRepoRulesetsRequest):
    """
    Update repository rulesets for multiple repositories.
    
    Updates:
    - Adds specified repositories to an existing ruleset
    - Maintains existing repositories in the ruleset
    - Returns the original and updated repository lists
    
    Requires:
    - Organization name
    - Ruleset name
    - List of repository names to add
    """
    try:
        return await project_service.put_repo_rulesets(request)
    except ValueError as e:
        logger.error(f"Validation error in put_repo_rulesets: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in put_repo_rulesets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/teams/members")
async def add_team_members(request: TeamMembershipRequest):
    """
    Add members to teams associated with a repository.
    
    Adds specified users to the corresponding teams with the repository prefix.
    Each team name will be prefixed with the repository name.
    """
    try:
        return await project_service.update_team_members(
            request.org_name,
            [team.dict() for team in request.teams]
        )
    except Exception as e:
        logger.error(f"Error adding team members: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/teams/members")
async def remove_team_members(request: TeamMembershipRequest):
    """
    Remove members from teams associated with a repository.
    
    Removes specified users from the corresponding teams with the repository prefix.
    Each team name will be prefixed with the repository name.
    """
    try:
        return await project_service.remove_team_members(
            request.org_name,
            [team.dict() for team in request.teams]
        )
    except Exception as e:
        logger.error(f"Error removing team members: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))