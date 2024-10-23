from fastapi import APIRouter, HTTPException
from models.project_models import (
    CreateProjectRequest, DeleteProjectRequest, DeleteTeamRequest,
    DeleteSonarRequest, UpdatedRepoPermission, UpdateMultiRepoPermission,
    CreateMultiProjectRequest, DeleteMultiProjectRequest
)
from services.project_service import ProjectService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
project_service = ProjectService()

@router.post("/create_project")
async def create_project(request: CreateProjectRequest):
    try:
        return await project_service.create_project(request)
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_multi_project")
async def create_multi_project(request: CreateMultiProjectRequest):
    try:
        return await project_service.create_multi_project(request)
    except Exception as e:
        logger.error(f"Error creating multi-project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update_repo_permission")
async def update_repo_permission(request: UpdatedRepoPermission):
    try:
        return await project_service.update_repo_permission(request)
    except Exception as e:
        logger.error(f"Error updating repository permission: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete_project")
async def delete_project(request: DeleteProjectRequest):
    try:
        return await project_service.delete_project(request.org_name, request.repo_name)
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete_multi_project")
async def delete_multi_project(request: DeleteMultiProjectRequest):
    try:
        return await project_service.delete_multi_project(
            request.org_name,
            request.repo_names
        )
    except Exception as e:
        logger.error(f"Error in delete_multi_project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))