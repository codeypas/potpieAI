import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class AICodeReviewer:
    """AI-powered code review agent"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4-turbo-preview"
    
    @staticmethod
    def _is_code_file(filename: str) -> bool:
        """Check if file is a code file"""
        code_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php', '.swift'}
        return any(filename.endswith(ext) for ext in code_extensions)
    
    def analyze_code(self, file_content: str, file_name: str) -> Dict:
        """
        Analyze code for issues using AI
        Add proper error handling and fallback analysis
        """
        try:
            max_lines = 100
            lines = file_content.split('\n')[:max_lines]
            truncated_content = '\n'.join(lines)
            
            prompt = f"""Analyze this code file for issues. Return ONLY valid JSON with this exact structure:
{{
    "issues": [
        {{"line": 1, "type": "style|bug|performance|best_practice", "description": "...", "suggestion": "..."}}
    ]
}}

File: {file_name}

{truncated_content}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a code review expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                timeout=30
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if '```' in result_text:
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            data = json.loads(result_text)
            
            return {
                "name": file_name,
                "issues": data.get("issues", [])
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {file_name}: {str(e)}")
            return {"name": file_name, "issues": []}
        except Exception as e:
            logger.error(f"Error analyzing code: {str(e)}")
            return {"name": file_name, "issues": []}
    
    def analyze_pr(self, pr_files: List[Dict], file_contents: Dict) -> Dict:
        """
        Improved PR analysis with summary statistics
        """
        all_issues = []
        results_files = []
        
        for file_data in pr_files:
            file_name = file_data.get("filename", "")
            
            if not self._is_code_file(file_name):
                continue
            
            if file_contents.get(file_name):
                analysis = self.analyze_code(file_contents[file_name], file_name)
                if analysis["issues"]:
                    all_issues.extend(analysis["issues"])
                    results_files.append(analysis)
        
        critical_issues = len([i for i in all_issues if i.get("type") == "bug"])
        
        return {
            "files": results_files,
            "summary": {
                "total_files": len(results_files),
                "total_issues": len(all_issues),
                "critical_issues": critical_issues
            }
        }
