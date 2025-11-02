"""
YouTube Subtitle Extractor - FastAPI Backend
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional
import uuid
import asyncio
import yt_dlp
import requests
import logging
from datetime import datetime
from enum import Enum

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
    """Helper class to extract subtitles from YouTube videos"""

    def __init__(self):
        self.preferred_languages = ["zh-TW", "zh-CN", "zh", "en"]

    async def extract(self, url: str, language_preference: Optional[list[str]] = None) -> dict:
        """Extract subtitles from a YouTube video"""
        if language_preference:
            self.preferred_languages = language_preference

        try:
            logger.info(f"Extracting subtitles from: {url}")

            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "quiet": False,
                "no_warnings": False,
                "subtitlesformat": "srt/best",
                "socket_timeout": 30,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-us,en;q=0.5",
                    "Sec-Fetch-Mode": "navigate"
                },
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web"],
                        "player_skip": ["webpage", "configs"]
                    }
                }
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                subtitles = info.get("subtitles", {})
                automatic_captions = info.get("automatic_captions", {})

                subtitle_data = self._get_best_subtitles(subtitles, automatic_captions)

                if subtitle_data:
                    logger.info(f"Successfully extracted subtitles: {subtitle_data['language']}")
                    return {
                        "success": True,
                        "content": subtitle_data["text"],
                        "language": subtitle_data["language"],
                        "title": info.get("title", "Unknown"),
                    }
                else:
                    return {"success": False, "error": "No subtitles found for this video"}

        except Exception as e:
            logger.error(f"Error extracting subtitles: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_best_subtitles(self, subtitles: dict, automatic_captions: dict) -> Optional[dict]:
        """Get the best available subtitles based on language preference"""
        # Check manual subtitles first
        for lang in self.preferred_languages:
            if lang in subtitles:
                return self._fetch_subtitle_content(subtitles[lang], lang)

        # Check automatic captions
        for lang in self.preferred_languages:
            if lang in automatic_captions:
                return self._fetch_subtitle_content(automatic_captions[lang], lang + " (Auto-generated)")

        # Use first available
        if subtitles:
            lang = list(subtitles.keys())[0]
            return self._fetch_subtitle_content(subtitles[lang], lang)

        if automatic_captions:
            lang = list(automatic_captions.keys())[0]
            return self._fetch_subtitle_content(automatic_captions[lang], lang + " (Auto-generated)")

        return None

    def _fetch_subtitle_content(self, subtitle_list: list, language: str) -> Optional[dict]:
        """Fetch and parse subtitle content"""
        try:
            if not subtitle_list:
                return None

            # JSON3 format
            if subtitle_list[0]["ext"] == "json3":
                response = requests.get(subtitle_list[0]["url"], timeout=10)
                data = response.json()
                text = ""
                for event in data.get("events", []):
                    if "segs" in event:
                        for seg in event["segs"]:
                            text += seg.get("utf8", "")
                return {"text": text, "language": language}

            # VTT or SRT format
            else:
                response = requests.get(subtitle_list[0]["url"], timeout=10)
                content = response.text
                lines = content.split("\n")
                subtitle_text = []
                for line in lines:
                    # Skip empty lines, timestamps, and sequence numbers
                    if line.strip() and "-->" not in line and not line.isdigit():
                        subtitle_text.append(line.strip())

                return {"text": "\n".join(subtitle_text), "language": language}

        except Exception as e:
            logger.error(f"Error fetching subtitle content: {e}")
            return None


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
