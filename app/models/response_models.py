from typing import List
from pydantic import BaseModel

class TeamInfo(BaseModel):
    name: str
    permission: str

class ProjectSummary(BaseModel):
    repo_name: str
    teams: List[TeamInfo]
    sonar_project_key: str
    sonar_token: str

class MultiProjectResponse(BaseModel):
    message: str
    projects: List[ProjectSummary]