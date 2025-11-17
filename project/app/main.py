from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
import logging
from datetime import datetime
import os

from app.database import get_db, init_db
from app.models import CodeReviewTask
from app.tasks import analyze_github_pr, celery_app
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="AI Code Review System",
    description="Autonomous agent for analyzing GitHub pull requests",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()
    logger.info("Database initialized")

# Request/Response Models
class AnalyzePRRequest(BaseModel):
    repo_url: str
    pr_number: int
    github_token: str = None

class TaskStatus(BaseModel):
    task_id: str
    status: str
    created_at: datetime
    updated_at: datetime

class TaskResult(BaseModel):
    task_id: str
    status: str
    results: dict = None
    error_message: str = None

# Endpoints
@app.get("/")
async def root():
    """Serve dashboard UI"""
    return HTMLResponse(get_dashboard_html())

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "AI Code Review System",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.post("/analyze-pr")
async def analyze_pr(request: AnalyzePRRequest, db: Session = Depends(get_db)):
    """
    Queue a PR for analysis
    """
    try:
        if "github.com" not in request.repo_url:
            raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
        
        if request.pr_number <= 0:
            raise HTTPException(status_code=400, detail="PR number must be positive")
        
        logger.info(f"Queuing analysis for {request.repo_url}#{request.pr_number}")
        
        # Create task in database
        task = CodeReviewTask(
            repo_url=request.repo_url,
            pr_number=str(request.pr_number),
            status="pending"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Queue Celery task
        analyze_github_pr.delay(
            task.task_id,
            request.repo_url,
            request.pr_number,
            request.github_token
        )
        
        return {
            "task_id": task.task_id,
            "status": "pending",
            "message": "PR analysis queued successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing PR analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}")
async def get_status(task_id: str, db: Session = Depends(get_db)):
    """
    Get status of an analysis task with proper null handling
    """
    task = db.query(CodeReviewTask).filter(CodeReviewTask.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {
        "task_id": task.task_id,
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "repo_url": task.repo_url,
        "pr_number": task.pr_number
    }

@app.get("/results/{task_id}")
async def get_results(task_id: str, db: Session = Depends(get_db)):
    """
    Get analysis results with proper error handling
    """
    task = db.query(CodeReviewTask).filter(CodeReviewTask.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    result = {
        "task_id": task.task_id,
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "error_message": task.error_message
    }
    
    if task.results:
        try:
            result["results"] = json.loads(task.results)
        except json.JSONDecodeError:
            result["results"] = None
            result["error_message"] = "Invalid results JSON"
    
    return result

@app.get("/tasks")
async def list_tasks(db: Session = Depends(get_db), limit: int = 10):
    """
    List recent tasks
    """
    tasks = db.query(CodeReviewTask).order_by(CodeReviewTask.created_at.desc()).limit(limit).all()
    
    return [
        {
            "task_id": task.task_id,
            "repo_url": task.repo_url,
            "pr_number": task.pr_number,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }
        for task in tasks
    ]

def get_dashboard_html() -> str:
    """Return clean dashboard UI"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Code Review System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        .status-pending { background-color: #fef3c7; color: #92400e; }
        .status-processing { background-color: #dbeafe; color: #1e40af; }
        .status-completed { background-color: #dcfce7; color: #166534; }
        .status-failed { background-color: #fee2e2; color: #991b1b; }
    </style>
</head>
<body class="bg-gradient-to-br from-slate-900 to-slate-800 text-white min-h-screen">
    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-4xl font-bold mb-2">AI Code Review System</h1>
            <p class="text-slate-400">Autonomous agent for analyzing GitHub pull requests</p>
        </div>

        <!-- Main Content -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <!-- Input Form -->
            <div class="lg:col-span-2 bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h2 class="text-xl font-bold mb-4">Analyze Pull Request</h2>
                <form id="analyzeForm" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium mb-2">Repository URL</label>
                        <input type="text" id="repoUrl" placeholder="https://github.com/owner/repo" 
                               class="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400"
                               required>
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-2">PR Number</label>
                        <input type="number" id="prNumber" placeholder="123" 
                               class="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400"
                               required>
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-2">GitHub Token (Optional)</label>
                        <input type="password" id="githubToken" placeholder="ghp_..." 
                               class="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400">
                        <small class="text-slate-400 mt-1">For private repos or higher rate limits</small>
                    </div>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-medium transition">
                        Submit Analysis
                    </button>
                </form>
            </div>

            <!-- Stats -->
            <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h2 class="text-xl font-bold mb-4">Stats</h2>
                <div class="space-y-3">
                    <div>
                        <p class="text-slate-400 text-sm">Total Tasks</p>
                        <p class="text-3xl font-bold" id="totalTasks">0</p>
                    </div>
                    <div>
                        <p class="text-slate-400 text-sm">Completed</p>
                        <p class="text-3xl font-bold text-green-400" id="completedTasks">0</p>
                    </div>
                    <div>
                        <p class="text-slate-400 text-sm">Failed</p>
                        <p class="text-3xl font-bold text-red-400" id="failedTasks">0</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tasks List -->
        <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 class="text-xl font-bold mb-4">Recent Tasks</h2>
            <div id="tasksList" class="space-y-3">
                <p class="text-slate-400">No tasks yet</p>
            </div>
        </div>

        <!-- Results Modal -->
        <div id="resultsModal" class="hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div class="bg-slate-800 rounded-lg max-w-2xl w-full max-h-96 overflow-y-auto border border-slate-700">
                <div class="p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-bold">Analysis Results</h3>
                        <button onclick="closeModal()" class="text-slate-400 hover:text-white">✕</button>
                    </div>
                    <div id="resultsContent" class="space-y-4 text-sm"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_URL = window.location.origin;

        document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const repoUrl = document.getElementById('repoUrl').value;
            const prNumber = parseInt(document.getElementById('prNumber').value);
            const githubToken = document.getElementById('githubToken').value || null;

            try {
                const response = await fetch(`${API_URL}/analyze-pr`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ repo_url: repoUrl, pr_number: prNumber, github_token: githubToken })
                });

                if (!response.ok) throw new Error(await response.text());
                const data = await response.json();
                alert(`Analysis queued! Task ID: ${data.task_id}`);
                document.getElementById('analyzeForm').reset();
                loadTasks();
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        });

        async function loadTasks() {
            try {
                const response = await fetch(`${API_URL}/tasks?limit=20`);
                const tasks = await response.json();

                let completed = 0, failed = 0;
                let html = '';

                for (const task of tasks) {
                    const status = task.status;
                    if (status === 'completed') completed++;
                    if (status === 'failed') failed++;

                    html += `
                        <div class="bg-slate-700 p-4 rounded border border-slate-600 flex justify-between items-center">
                            <div>
                                <p class="font-medium">${task.repo_url.split('/').slice(-2).join('/')}</p>
                                <p class="text-sm text-slate-400">PR #${task.pr_number}</p>
                            </div>
                            <div class="flex gap-2 items-center">
                                <span class="status-badge status-${status}">${status}</span>
                                ${status === 'completed' ? `<button onclick="viewResults('${task.task_id}')" class="text-blue-400 hover:text-blue-300 text-sm">View</button>` : ''}
                            </div>
                        </div>
                    `;
                }

                document.getElementById('tasksList').innerHTML = html || '<p class="text-slate-400">No tasks yet</p>';
                document.getElementById('totalTasks').textContent = tasks.length;
                document.getElementById('completedTasks').textContent = completed;
                document.getElementById('failedTasks').textContent = failed;
            } catch (error) {
                console.error('Error loading tasks:', error);
            }
        }

        async function viewResults(taskId) {
            try {
                const response = await fetch(`${API_URL}/results/${taskId}`);
                const data = await response.json();

                let html = '';
                if (data.status === 'completed' && data.results) {
                    const results = data.results;
                    html += `<p class="mb-2"><strong>Files Analyzed:</strong> ${results.summary.total_files}</p>`;
                    html += `<p class="mb-2"><strong>Total Issues:</strong> ${results.summary.total_issues}</p>`;
                    html += `<p class="mb-4"><strong>Critical Issues:</strong> ${results.summary.critical_issues}</p>`;

                    for (const file of results.files) {
                        html += `<p class="font-medium text-blue-400 mb-2">${file.name}</p>`;
                        if (file.issues.length > 0) {
                            for (const issue of file.issues) {
                                html += `<p class="text-xs ml-4 mb-1">• <strong>[${issue.type}]</strong> Line ${issue.line}: ${issue.description}</p>`;
                            }
                        } else {
                            html += `<p class="text-xs ml-4 text-green-400 mb-2">✓ No issues found</p>`;
                        }
                    }
                } else if (data.error_message) {
                    html = `<p class="text-red-400">${data.error_message}</p>`;
                } else {
                    html = `<p class="text-yellow-400">Status: ${data.status}</p>`;
                }

                document.getElementById('resultsContent').innerHTML = html;
                document.getElementById('resultsModal').classList.remove('hidden');
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        function closeModal() {
            document.getElementById('resultsModal').classList.add('hidden');
        }

        // Auto-refresh tasks
        loadTasks();
        setInterval(loadTasks, 5000);
    </script>
</body>
</html>
"""
