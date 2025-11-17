import json
import logging
from typing import Dict, List, Optional
from langchain.chat_models import ChatOllama
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
from app.config import settings

logger = logging.getLogger(__name__)

class StyleAnalysisAgent:
    """Agent specialized in code style and formatting analysis"""
    
    def __init__(self):
        self.llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.3,
            num_predict=500
        )
    
    def analyze(self, code: str, filename: str) -> List[Dict]:
        """Analyze code for style and formatting issues"""
        try:
            prompt = f"""Analyze this code file for STYLE and FORMATTING issues only. Return JSON array.

File: {filename}
Code:
{code}

Return ONLY this JSON format (array of objects with: line, type, description, suggestion):
[]

Look for: long lines, indentation, spacing, naming conventions."""

            messages = [
                SystemMessage(content="You are a code style expert. Return ONLY valid JSON, no other text."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            text = response.content.strip()
            
            # Extract JSON from response
            if '[' in text and ']' in text:
                json_str = text[text.find('['):text.rfind(']')+1]
                return json.loads(json_str)
            return []
        except Exception as e:
            logger.error(f"Style analysis error: {str(e)}")
            return []

class BugAnalysisAgent:
    """Agent specialized in bug and error detection"""
    
    def __init__(self):
        self.llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.3,
            num_predict=500
        )
    
    def analyze(self, code: str, filename: str) -> List[Dict]:
        """Analyze code for potential bugs and errors"""
        try:
            prompt = f"""Analyze this code file for BUGS and ERROR-PRONE code. Return JSON array.

File: {filename}
Code:
{code}

Return ONLY this JSON format (array of objects with: line, type, description, suggestion):
[]

Look for: null pointer risks, uncaught exceptions, logic errors, off-by-one errors."""

            messages = [
                SystemMessage(content="You are a code bug detection expert. Return ONLY valid JSON, no other text."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            text = response.content.strip()
            
            if '[' in text and ']' in text:
                json_str = text[text.find('['):text.rfind(']')+1]
                return json.loads(json_str)
            return []
        except Exception as e:
            logger.error(f"Bug analysis error: {str(e)}")
            return []

class PerformanceAnalysisAgent:
    """Agent specialized in performance optimization"""
    
    def __init__(self):
        self.llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.3,
            num_predict=500
        )
    
    def analyze(self, code: str, filename: str) -> List[Dict]:
        """Analyze code for performance improvement opportunities"""
        try:
            prompt = f"""Analyze this code file for PERFORMANCE issues. Return JSON array.

File: {filename}
Code:
{code}

Return ONLY this JSON format (array of objects with: line, type, description, suggestion):
[]

Look for: inefficient algorithms, N+1 queries, memory leaks, unnecessary loops."""

            messages = [
                SystemMessage(content="You are a performance optimization expert. Return ONLY valid JSON, no other text."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            text = response.content.strip()
            
            if '[' in text and ']' in text:
                json_str = text[text.find('['):text.rfind(']')+1]
                return json.loads(json_str)
            return []
        except Exception as e:
            logger.error(f"Performance analysis error: {str(e)}")
            return []

class BestPracticesAnalysisAgent:
    """Agent specialized in best practices and code quality"""
    
    def __init__(self):
        self.llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.3,
            num_predict=500
        )
    
    def analyze(self, code: str, filename: str) -> List[Dict]:
        """Analyze code for best practice violations"""
        try:
            prompt = f"""Analyze this code file for BEST PRACTICES violations. Return JSON array.

File: {filename}
Code:
{code}

Return ONLY this JSON format (array of objects with: line, type, description, suggestion):
[]

Look for: DRY violations, missing error handling, security issues, bad imports."""

            messages = [
                SystemMessage(content="You are a code best practices expert. Return ONLY valid JSON, no other text."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            text = response.content.strip()
            
            if '[' in text and ']' in text:
                json_str = text[text.find('['):text.rfind(']')+1]
                return json.loads(json_str)
            return []
        except Exception as e:
            logger.error(f"Best practices analysis error: {str(e)}")
            return []

class CodeReviewOrchestrator:
    """Orchestrates multiple agents for comprehensive code review"""
    
    def __init__(self):
        self.style_agent = StyleAnalysisAgent()
        self.bug_agent = BugAnalysisAgent()
        self.performance_agent = PerformanceAnalysisAgent()
        self.best_practices_agent = BestPracticesAnalysisAgent()
    
    @staticmethod
    def _is_code_file(filename: str) -> bool:
        """Check if file is a code file"""
        code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', 
            '.cpp', '.c', '.rb', '.php', '.swift', '.kt', '.scala', '.sh'
        }
        return any(filename.endswith(ext) for ext in code_extensions)
    
    def analyze_file(self, code: str, filename: str) -> Dict:
        """Analyze single file with all agents"""
        logger.info(f"Starting multi-agent analysis for {filename}")
        
        all_issues = []
        
        # Run all agents in parallel conceptually (sequentially for simplicity)
        logger.info(f"Running style analysis for {filename}")
        style_issues = self.style_agent.analyze(code, filename)
        all_issues.extend([{**issue, 'type': 'style'} for issue in style_issues])
        
        logger.info(f"Running bug analysis for {filename}")
        bug_issues = self.bug_agent.analyze(code, filename)
        all_issues.extend([{**issue, 'type': 'bug'} for issue in bug_issues])
        
        logger.info(f"Running performance analysis for {filename}")
        perf_issues = self.performance_agent.analyze(code, filename)
        all_issues.extend([{**issue, 'type': 'performance'} for issue in perf_issues])
        
        logger.info(f"Running best practices analysis for {filename}")
        bp_issues = self.best_practices_agent.analyze(code, filename)
        all_issues.extend([{**issue, 'type': 'best_practice'} for issue in bp_issues])
        
        # Remove duplicates and limit to 10 most important
        seen = set()
        unique_issues = []
        for issue in all_issues:
            key = (issue.get('line'), issue.get('description'))
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)
        
        return {
            "name": filename,
            "issues": unique_issues[:10]
        }
    
    def analyze_pr(self, pr_files: List[Dict], file_contents: Dict) -> Dict:
        """Analyze entire PR using multi-agent system"""
        logger.info("Starting PR analysis with multi-agent orchestrator")
        
        all_issues = []
        results_files = []
        
        for file_data in pr_files:
            filename = file_data.get("filename", "")
            
            if not self._is_code_file(filename):
                logger.debug(f"Skipping non-code file: {filename}")
                continue
            
            if filename not in file_contents:
                logger.warning(f"No content available for {filename}")
                continue
            
            code = file_contents[filename]
            if not code or len(code) == 0:
                logger.warning(f"Empty file: {filename}")
                continue
            
            # Limit file size to 10KB for analysis
            if len(code) > 10000:
                code = code[:10000]
                logger.info(f"Truncated {filename} to 10KB")
            
            analysis = self.analyze_file(code, filename)
            if analysis["issues"]:
                all_issues.extend(analysis["issues"])
                results_files.append(analysis)
        
        critical_issues = len([i for i in all_issues if i.get("type") == "bug"])
        
        summary = {
            "total_files": len(results_files),
            "total_issues": len(all_issues),
            "critical_issues": critical_issues,
            "agent_used": "LangChain Multi-Agent (Ollama)"
        }
        
        logger.info(f"PR analysis complete: {summary}")
        
        return {
            "files": results_files,
            "summary": summary
        }
