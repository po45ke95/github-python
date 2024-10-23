from pydantic import BaseModel
from typing import Literal, List

class CreateProjectRequest(BaseModel):
    org_name: str
    repo_name: str
    team_name: str
    team_permission: str = 'push'

class UpdatedRepoPermission(BaseModel):
    org_name: str
    repo_name: str
    team_name: str
    new_permission: Literal['pull', 'triage', 'push', 'maintain', 'admin'] = 'push'

class UpdateMultiRepoPermission(BaseModel):
    org_name: str
    repo_names: List[str]
    team_names: List[str]
    new_permission: str

class DeleteProjectRequest(BaseModel):
    org_name: str
    repo_name: str

class DeleteTeamRequest(BaseModel):
    org_name: str
    team_name: str

class DeleteSonarRequest(BaseModel):
    org_name: str
    repo_name: str

class CreateMultiProjectRequest(BaseModel):
    org_name: str
    repo_names: List[str]

class DeleteMultiProjectRequest(BaseModel):
    org_name: str
    repo_names: List[str]