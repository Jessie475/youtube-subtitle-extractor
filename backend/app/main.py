"""
YouTube Subtitle Extractor - FastAPI Backend
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional
import uuid
import asyncio
import re
import logging
from datetime import datetime
from enum import Enum
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube Subtitle Extractor API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://subtitles.kokonut.us.kg"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task store (could be upgraded to Redis/Database later)
task_store = {}


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubtitleRequest(BaseModel):
    url: str
    language_preference: Optional[list[str]] = ["zh-TW", "zh-CN", "zh", "en"]


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    progress: Optional[int] = None


class SubtitleResponse(BaseModel):
    task_id: str
    status: TaskStatus
    content: Optional[str] = None
    language: Optional[str] = None
    message: str


class SubtitleExtractor:
    """Helper class to extract subtitles from YouTube videos using YouTube Transcript API"""

    def __init__(self):
        self.preferred_languages = ["zh-TW", "zh-CN", "zh", "en"]

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def extract(self, url: str, language_preference: Optional[list[str]] = None) -> dict:
        """Extract subtitles from a YouTube video"""
        if language_preference:
            self.preferred_languages = language_preference

        try:
            logger.info(f"Extracting subtitles from: {url}")

            # Extract video ID
            video_id = self._extract_video_id(url)
            if not video_id:
                return {"success": False, "error": "Invalid YouTube URL"}

            logger.info(f"Video ID: {video_id}")

            # Try to get transcript list
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to find preferred language (manual subtitles first)
            transcript = None
            selected_language = None
            is_auto_generated = False

            # First, try manual subtitles in preferred languages
            for lang in self.preferred_languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    selected_language = lang
                    is_auto_generated = transcript.is_generated
                    logger.info(f"Found manual subtitle in {lang}")
                    break
                except:
                    continue

            # If no manual subtitles, try auto-generated in preferred languages
            if not transcript:
                for lang in self.preferred_languages:
                    try:
                        transcript = transcript_list.find_generated_transcript([lang])
                        selected_language = lang
                        is_auto_generated = True
                        logger.info(f"Found auto-generated subtitle in {lang}")
                        break
                    except:
                        continue

            # If still no transcript, get any available transcript
            if not transcript:
                try:
                    # Get first available transcript
                    for t in transcript_list:
                        transcript = t
                        selected_language = t.language_code
                        is_auto_generated = t.is_generated
                        logger.info(f"Using first available subtitle: {selected_language}")
                        break
                except:
                    pass

            if not transcript:
                return {"success": False, "error": "No subtitles available for this video"}

            # Fetch the actual transcript
            transcript_data = transcript.fetch()

            # Format the transcript
            formatter = TextFormatter()
            subtitle_text = formatter.format_transcript(transcript_data)

            language_label = selected_language
            if is_auto_generated:
                language_label += " (Auto-generated)"

            logger.info(f"Successfully extracted subtitles: {language_label}")

            return {
                "success": True,
                "content": subtitle_text,
                "language": language_label,
                "title": f"Video {video_id}",  # Transcript API doesn't provide title
            }

        except Exception as e:
            logger.error(f"Error extracting subtitles: {str(e)}")
            return {"success": False, "error": str(e)}


def process_subtitle_extraction(task_id: str, url: str, language_preference: Optional[list[str]]):
    """Background task to extract subtitles"""
    try:
        task_store[task_id]["status"] = TaskStatus.PROCESSING
        task_store[task_id]["progress"] = 25

        extractor = SubtitleExtractor()
        result = asyncio.run(extractor.extract(url, language_preference))

        if result["success"]:
            task_store[task_id]["status"] = TaskStatus.COMPLETED
            task_store[task_id]["content"] = result["content"]
            task_store[task_id]["language"] = result["language"]
            task_store[task_id]["title"] = result["title"]
            task_store[task_id]["progress"] = 100
            task_store[task_id]["message"] = f"Successfully extracted subtitles ({result['language']})"
        else:
            task_store[task_id]["status"] = TaskStatus.FAILED
            task_store[task_id]["message"] = result["error"]
            task_store[task_id]["progress"] = 0

    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["message"] = str(e)


# API Routes


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/subtitles/extract", response_model=TaskResponse)
async def extract_subtitles(request: SubtitleRequest, background_tasks: BackgroundTasks):
    """
    Submit a subtitle extraction task
    Returns a task ID for checking status
    """
    task_id = str(uuid.uuid4())

    task_store[task_id] = {
        "status": TaskStatus.PENDING,
        "message": "Task queued",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "url": request.url,
        "content": None,
        "language": None,
        "title": None,
    }

    # Start background task
    background_tasks.add_task(
        process_subtitle_extraction, task_id, request.url, request.language_preference
    )

    return TaskResponse(task_id=task_id, status=TaskStatus.PENDING, message="Task submitted")


@app.get("/subtitles/status/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Get the status of a subtitle extraction task"""
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_store[task_id]
    return TaskResponse(
        task_id=task_id,
        status=task["status"],
        message=task["message"],
        progress=task["progress"],
    )


@app.get("/subtitles/result/{task_id}", response_model=SubtitleResponse)
async def get_task_result(task_id: str):
    """Get the result of a completed subtitle extraction task"""
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_store[task_id]

    if task["status"] != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Task is {task['status']}. Message: {task['message']}",
        )

    return SubtitleResponse(
        task_id=task_id,
        status=task["status"],
        content=task["content"],
        language=task["language"],
        message=task["message"],
    )


@app.delete("/subtitles/{task_id}")
async def delete_task(task_id: str):
    """Delete a task from the store"""
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    del task_store[task_id]
    return {"message": "Task deleted"}


@app.get("/")
async def root():
    """API documentation"""
    return {
        "name": "YouTube Subtitle Extractor API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "extract": "POST /subtitles/extract",
            "status": "GET /subtitles/status/{task_id}",
            "result": "GET /subtitles/result/{task_id}",
            "delete": "DELETE /subtitles/{task_id}",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
