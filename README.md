# Project Setup API

This FastAPI application automates the process of setting up new projects, including creating GitHub repositories, managing teams, and configuring SonarQube for code quality analysis.

## Features

- Create new GitHub repositories from a template
- Create or use existing GitHub teams
- Add repositories to teams with specified permissions
- Create SonarQube projects and generate analysis tokens
- Add SonarQube configuration as GitHub secrets
- Delete projects and clean up associated resources

## Prerequisites

- Python 3.12.0
- FastAPI 0.85.0
- Requests 2.31.0
- PyYAML 6.0.2
- PyNaCl 1.5.0

## Configuration

The application uses a `config.yaml` file for configuration. Ensure this file is present in the same directory as the script with the following structure:

```yaml
github:
  token: YOUR_GITHUB_TOKEN
  template_owner: TEMPLATE_REPO_OWNER
  template_repo: TEMPLATE_REPO_NAME

sonarqube:
  url: YOUR_SONARQUBE_URL
  token: YOUR_SONARQUBE_TOKEN

certificates:
  github: PATH_TO_GITHUB_CA_CERT
  sonarqube: PATH_TO_SONARQUBE_CA_CERT
```

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```bash
   pip install fastapi pydantic requests pyyaml pynacl uvicorn
   ```
3. Set up your `config.yaml` file with the necessary credentials and configurations
4. Ensure the CA certificate files for GitHub and SonarQube are in the same directory as the script

## Usage

Start the FastAPI server:

```bash
python main.py
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Create Project
```http
POST /create_project
```

Creates a new single project setup including GitHub repository and associated resources.

**Request Body Schema**: `CreateProjectRequest`

### Create Multiple Projects
```http
POST /create_multi_project
```

Creates multiple projects simultaneously.

**Request Body Schema**: `CreateMultiProjectRequest`

### Update Repository Permission
```http
PUT /update_repo_permission
```

Updates the permission settings for a repository.

**Request Body Schema**: `UpdatedRepoPermission`

### Delete Project
```http
DELETE /delete_project
```

Deletes a single project and all its associated resources.

**Request Body Schema**: `DeleteProjectRequest`
```json
{
    "org_name": "string",    // Organization name
    "repo_name": "string"    // Repository name
}
```

### Delete Multiple Projects
```http
DELETE /delete_multi_project
```

Deletes multiple projects and their associated resources simultaneously.

**Request Body Schema**: `DeleteMultiProjectRequest`
```json
{
    "org_name": "string",      // Organization name
    "repo_names": ["string"]   // List of repository names
}
```

### Request Models

Each endpoint uses specific request models for data validation:
- `CreateProjectRequest`
- `CreateMultiProjectRequest`
- `UpdatedRepoPermission`
- `DeleteProjectRequest`
- `DeleteMultiProjectRequest`

### Response Codes

| Status Code | Description |
|------------|-------------|
| 200 | Operation successful |
| 500 | Internal Server Error with error details |

## Github Team API Permissions

| Api Request Body | Api Permission |
|------------------|----------------|
| pull | Read |
| triage | Triage |
| push | Write |
| maintain | Maintain |
| admin | Admin |

## Error Handling

The application includes comprehensive error handling and logging. Check the console output for detailed information about operations and any errors that occur.

## Security Notes

- Ensure that your `config.yaml` file and CA certificate files are kept secure and not exposed publicly
- The application uses HTTPS for all API calls to GitHub and SonarQube
- Secrets are encrypted before being sent to GitHub

## API Framework
- [FastAPI](https://fastapi.tiangolo.com/zh/)