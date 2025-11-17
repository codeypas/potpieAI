from celery import Celery
from app.config import settings
from app.github_service import GitHubService
from app.ai_agent import CodeReviewOrchestrator
from app.database import SessionLocal
from app.models import CodeReviewTask
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'code_review_system',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
)

@celery_app.task(bind=True, name='analyze_github_pr', max_retries=2)
def analyze_github_pr(self, task_id: str, repo_url: str, pr_number: int, github_token: str = None):
    """
    Updated to use Ollama + LangChain multi-agent instead of OpenAI
    Celery task: Analyze GitHub PR with multi-agent orchestrator
    """
    db = SessionLocal()
    
    try:
        logger.info(f"[Task {task_id}] Starting analysis for {repo_url}#{pr_number}")
        
        # Update status to processing
        task = db.query(CodeReviewTask).filter(CodeReviewTask.task_id == task_id).first()
        if task:
            task.status = "processing"
            task.updated_at = datetime.utcnow()
            db.commit()
        
        # Step 1: Fetch PR files
        logger.info(f"[Task {task_id}] Fetching PR files...")
        gh_service = GitHubService(github_token)
        pr_files = gh_service.get_pr_files(repo_url, pr_number)
        
        if not pr_files:
            raise Exception("No code files found in PR or PR not accessible (may need valid GitHub token)")
        
        # Step 2: Get file contents
        logger.info(f"[Task {task_id}] Fetching file contents...")
        file_contents = {}
        
        for file_data in pr_files[:15]:  # Limit to 15 files
            filename = file_data.get("filename", "")
            logger.info(f"[Task {task_id}] Fetching content for {filename}...")
            
            try:
                content = gh_service.get_file_content(repo_url, f"pull/{pr_number}/head", filename)
                if content and len(content) < 100000:
                    file_contents[filename] = content
            except Exception as e:
                logger.warning(f"[Task {task_id}] Could not fetch {filename}: {str(e)}")
        
        logger.info(f"[Task {task_id}] Retrieved content for {len(file_contents)} files")
        
        # Step 3: Run multi-agent analysis
        logger.info(f"[Task {task_id}] Starting multi-agent analysis...")
        orchestrator = CodeReviewOrchestrator()
        analysis_results = orchestrator.analyze_pr(pr_files, file_contents)
        
        # Step 4: Update task with results
        task = db.query(CodeReviewTask).filter(CodeReviewTask.task_id == task_id).first()
        if task:
            task.status = "completed"
            task.results = json.dumps(analysis_results)
            task.error_message = None
            task.updated_at = datetime.utcnow()
            db.commit()
        
        logger.info(f"[Task {task_id}] Analysis completed successfully")
        return analysis_results
    
    except Exception as e:
        logger.error(f"[Task {task_id}] Error: {str(e)}")
        
        try:
            task = db.query(CodeReviewTask).filter(CodeReviewTask.task_id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = str(e)
                task.updated_at = datetime.utcnow()
                db.commit()
        except Exception as db_error:
            logger.error(f"[Task {task_id}] Database error: {str(db_error)}")
        
        if "not configured" in str(e) or "No code files" in str(e):
            raise e
        
        raise self.retry(exc=e, countdown=5)
    
    finally:
        db.close()
