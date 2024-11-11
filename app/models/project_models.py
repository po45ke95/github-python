from pydantic import BaseModel, validator
from typing import Literal, List, Optional

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

class RepoConfig(BaseModel):
    region: str
    division: str  
    department: str
    system: str
    topics: Optional[List[str]] = []

    @property
    def name(self) -> str:
        return f"{self.region}-{self.division}-{self.department}-{self.system}"

    @validator('region', 'division', 'department', 'system')
    def validate_name_parts(cls, v: str) -> str:
        if '-' in v:
            raise ValueError("Name parts cannot contain hyphens")
        return v.strip()

class CreateMultiProjectRequest(BaseModel):
    org_name: str
    repo_names: List[RepoConfig]

class DeleteMultiProjectRequest(BaseModel):
    org_name: str
    repo_names: List[str]

class PutRepoRulesetsRequest(BaseModel):
    org_name: str
    rule_name: str
    repo_names: List[str]

class PutRepoRulesetsResponse(BaseModel):
    original_repos: List[str]
    updated_repos: List[str]
    added_repos: List[str]
    added_count: int
    message: str

class TeamMember(BaseModel):
    team_name: str
    member: List[str]

class TeamMembershipRequest(BaseModel):
    org_name: str
    teams: List[TeamMember]