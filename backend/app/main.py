"""
YouTube Subtitle Extractor - FastAPI Backend
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional
import uuid
import asyncio
import logging
from datetime import datetime
from enum import Enum
import yt_dlp
import requests
import os
import re
from app.proxy_manager import proxy_manager

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
    """Helper class to extract subtitles from YouTube videos using yt-dlp"""

    def __init__(self):
        self.preferred_languages = ["zh-TW", "zh-CN", "zh", "en"]

    async def extract(self, url: str, language_preference: Optional[list[str]] = None, proxy_url: Optional[str] = None) -> dict:
        """Extract subtitles from a YouTube video using yt-dlp"""
        if language_preference:
            self.preferred_languages = language_preference

        try:
            logger.info(f"Extracting subtitles from: {url}")

            # Simplified yt-dlp options focused only on subtitle extraction
            pot_provider_url = os.getenv("POT_PROVIDER_URL", "http://localhost:4416")
            logger.info(f"Using PO Token Provider at: {pot_provider_url}")

            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitlesformat": "json3",
                "socket_timeout": 120,
                "quiet": True,  # Reduce verbose output
                "no_warnings": True,
                "extractor_args": {
                    "youtubepot-bgutilhttp": {
                        "base_url": pot_provider_url
                    }
                },
            }

            # Add proxy if provided
            if proxy_url:
                ydl_opts["proxy"] = proxy_url
                # Hide credentials in log
                proxy_display = proxy_url.split('@')[1] if '@' in proxy_url else proxy_url
                logger.info(f"🔀 Using proxy: {proxy_display}")

            # Add cookies support if available
            cookie_file = os.getenv("YOUTUBE_COOKIES_FILE")
            if cookie_file and os.path.exists(cookie_file):
                ydl_opts["cookiefile"] = cookie_file
                logger.info(f"Using cookie file: {cookie_file}")

            logger.info(f"Extracting with yt-dlp...")

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
            logger.error(f"Error extracting subtitles with yt-dlp: {str(e)}")
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
    """Background task to extract subtitles with retry logic and proxy fallback"""
    import time

    extractor = SubtitleExtractor()
    task_store[task_id]["status"] = TaskStatus.PROCESSING
    task_store[task_id]["progress"] = 10

    # Step 1: Try without proxy first
    logger.info(f"Attempt 1: Extracting without proxy")
    result = asyncio.run(extractor.extract(url, language_preference, proxy_url=None))

    if result["success"]:
        task_store[task_id]["status"] = TaskStatus.COMPLETED
        task_store[task_id]["content"] = result["content"]
        task_store[task_id]["language"] = result["language"]
        task_store[task_id]["title"] = result["title"]
        task_store[task_id]["progress"] = 100
        task_store[task_id]["message"] = f"成功提取字幕 ({result['language']})"
        return

    # Check if error is bot detection related
    error_msg = result.get("error", "")
    is_bot_error = "bot" in error_msg.lower() or "sign in" in error_msg.lower()

    # Step 2: If failed and proxy fallback is enabled, try with proxies
    if is_bot_error and proxy_manager.is_enabled():
        logger.info("Bot detection error detected, trying with proxy fallback...")
        task_store[task_id]["progress"] = 30

        # Get 3 proxies to try
        proxies = proxy_manager.get_multiple_proxies(count=3)

        for i, proxy_url in enumerate(proxies):
            logger.info(f"Attempt {i + 2}: Trying with proxy {i + 1}/{len(proxies)}")
            task_store[task_id]["progress"] = 30 + (i * 20)

            time.sleep(5)  # Small delay between attempts

            result = asyncio.run(extractor.extract(url, language_preference, proxy_url=proxy_url))

            if result["success"]:
                task_store[task_id]["status"] = TaskStatus.COMPLETED
                task_store[task_id]["content"] = result["content"]
                task_store[task_id]["language"] = result["language"]
                task_store[task_id]["title"] = result["title"]
                task_store[task_id]["progress"] = 100
                task_store[task_id]["message"] = f"成功提取字幕 ({result['language']}) [使用代理]"
                logger.info(f"✅ Success with proxy {i + 1}")
                return
            else:
                logger.warning(f"Proxy {i + 1} failed: {result.get('error', 'Unknown')[:100]}")

    # All attempts failed
    task_store[task_id]["status"] = TaskStatus.FAILED
    task_store[task_id]["progress"] = 0

    # Enhanced error messages
    if is_bot_error:
        if proxy_manager.is_enabled():
            task_store[task_id]["message"] = f"YouTube 機器人檢測：即使使用代理也無法繞過。建議等待 5-10 分鐘後重試。"
        else:
            task_store[task_id]["message"] = f"YouTube 機器人檢測：{error_msg[:200]}。建議等待 5-10 分鐘後重試。"
    elif "403" in error_msg or "forbidden" in error_msg.lower():
        task_store[task_id]["message"] = f"訪問被拒：{error_msg[:200]}。可能是 IP 被暫時限制，請稍後重試。"
    elif "no subtitles" in error_msg.lower():
        task_store[task_id]["message"] = f"此影片沒有可用的字幕。"
    else:
        task_store[task_id]["message"] = error_msg[:300]


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
