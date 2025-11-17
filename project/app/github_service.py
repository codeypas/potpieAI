import requests
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class GitHubService:
    """Service to interact with GitHub API"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = self._get_headers()
    
    def _get_headers(self) -> Dict:
        """Get request headers"""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers
    
    def get_pr_files(self, repo_url: str, pr_number: int) -> List[Dict]:
        """Get PR files and changes with improved error handling"""
        try:
            parts = repo_url.rstrip('/').split('/')
            if len(parts) < 2:
                logger.error(f"Invalid repo URL format: {repo_url}")
                return []
            
            owner, repo = parts[-2], parts[-1]
            # Remove .git suffix if present
            repo = repo.replace('.git', '')
            
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files?per_page=100"
            logger.info(f"Fetching PR files from: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            files = response.json()
            logger.info(f"Retrieved {len(files)} files for PR #{pr_number}")
            return files
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error fetching PR files: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching PR files: {str(e)}")
            return []
    
    def get_file_content(self, repo_url: str, ref: str, file_path: str) -> Optional[str]:
        """Get file content from GitHub"""
        try:
            parts = repo_url.rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]
            repo = repo.replace('.git', '')
            
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}?ref={ref}"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 404:
                logger.warning(f"File not found: {file_path}")
                return None
            
            response.raise_for_status()
            
            import base64
            data = response.json()
            if 'content' in data:
                content = base64.b64decode(data['content']).decode('utf-8')
                return content
            return None
        except Exception as e:
            logger.error(f"Error fetching file content for {file_path}: {str(e)}")
            return None
    
    def get_pr_diff(self, repo_url: str, pr_number: int) -> Optional[str]:
        """Get full PR diff"""
        try:
            parts = repo_url.rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]
            repo = repo.replace('.git', '')
            
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            headers = self.headers.copy()
            headers["Accept"] = "application/vnd.github.v3.diff"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            return response.text
        except Exception as e:
            logger.error(f"Error fetching PR diff: {str(e)}")
            return None
