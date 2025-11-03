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
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    YouTubeRequestFailed,
    CouldNotRetrieveTranscript
)

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
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
            r'youtube\.com\/embed\/([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # If no pattern matches, assume it's already a video ID
        if len(url) == 11 and re.match(r'^[a-zA-Z0-9_-]+$', url):
            return url

        return None

    async def extract(self, url: str, language_preference: Optional[list[str]] = None) -> dict:
        """Extract subtitles from a YouTube video using YouTube Transcript API (primary) with yt-dlp fallback"""
        if language_preference:
            self.preferred_languages = language_preference

        try:
            logger.info(f"Extracting subtitles from: {url}")

            # Extract video ID from URL
            video_id = self._extract_video_id(url)
            if not video_id:
                return {"success": False, "error": "無法從 URL 中提取影片 ID"}

            logger.info(f"Video ID: {video_id}")

            # Try YouTube Transcript API first (uses YouTube's InnerTube API)
            try:
                return await self._extract_with_transcript_api(video_id)
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logger.warning(f"YouTube Transcript API failed: {str(e)}, falling back to yt-dlp")
                # Fallback to yt-dlp
                return await self._extract_with_ytdlp(url)
            except (VideoUnavailable, YouTubeRequestFailed, CouldNotRetrieveTranscript) as e:
                logger.error(f"YouTube Transcript API error: {str(e)}")
                return {"success": False, "error": f"YouTube API 錯誤: {str(e)}"}

        except Exception as e:
            logger.error(f"Error extracting subtitles: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _extract_with_transcript_api(self, video_id: str) -> dict:
        """Extract subtitles using YouTube Transcript API (InnerTube API)"""
        logger.info("Trying YouTube Transcript API (InnerTube)...")

        # Get list of available transcripts
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        # Try to find transcript in preferred language order
        transcript = None
        selected_language = None
        is_generated = False

        # First try manual transcripts
        for lang in self.preferred_languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                selected_language = lang
                is_generated = transcript.is_generated
                logger.info(f"Found manual transcript in language: {lang}")
                break
            except NoTranscriptFound:
                continue

        # If no manual transcript found, try auto-generated
        if not transcript:
            for lang in self.preferred_languages:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    selected_language = lang
                    is_generated = True
                    logger.info(f"Found auto-generated transcript in language: {lang}")
                    break
                except NoTranscriptFound:
                    continue

        # If still no transcript, use first available
        if not transcript:
            try:
                # Get first available transcript
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    transcript = available_transcripts[0]
                    selected_language = transcript.language_code
                    is_generated = transcript.is_generated
                    logger.info(f"Using first available transcript: {selected_language}")
            except Exception as e:
                raise NoTranscriptFound(video_id, [], str(e))

        if not transcript:
            raise NoTranscriptFound(video_id, self.preferred_languages, "No transcripts available")

        # Fetch the transcript
        transcript_data = transcript.fetch()

        # Combine all text segments
        full_text = "\n".join([entry.text for entry in transcript_data])

        language_label = f"{selected_language} {'(自動生成)' if is_generated else '(手動)'}"

        logger.info(f"Successfully extracted subtitles using YouTube Transcript API: {language_label}")

        return {
            "success": True,
            "content": full_text,
            "language": language_label,
            "title": f"Video {video_id}",  # Transcript API doesn't provide title
        }

    async def _extract_with_ytdlp(self, url: str) -> dict:
        """Fallback: Extract subtitles using yt-dlp"""
        logger.info("Using yt-dlp fallback method...")

        try:
            # Enhanced yt-dlp options to avoid bot detection with PO Token provider
            pot_provider_url = os.getenv("POT_PROVIDER_URL", "http://localhost:4416")
            logger.info(f"Using PO Token Provider at: {pot_provider_url}")

            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "quiet": False,
                "no_warnings": False,
                "verbose": True,  # Enable verbose logging to see plugin info
                "subtitlesformat": "json3",
                "socket_timeout": 120,  # Increased from 30 to 120 to handle Render cold starts
                # Try web client first (more lenient)
                "extractor_args": {
                    "youtube": {
                        "player_client": ["web", "mweb", "ios"],
                        "skip": ["hls", "dash"],
                        "player_skip": ["configs"]
                    },
                    "youtubepot-bgutilhttp": {
                        "base_url": pot_provider_url
                    }
                },
                # Add user agent to appear more like a browser
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            }

            # Add cookies support if available
            cookie_file = os.getenv("YOUTUBE_COOKIES_FILE")
            if cookie_file and os.path.exists(cookie_file):
                ydl_opts["cookiefile"] = cookie_file
                logger.info(f"Using cookie file: {cookie_file}")
            else:
                # Try to use browser cookies on local development
                try:
                    # This will only work in local environment, not on server
                    ydl_opts["cookiesfrombrowser"] = ("chrome",)
                    logger.info("Attempting to use Chrome browser cookies")
                except Exception as e:
                    logger.warning(f"Could not access browser cookies: {e}")

            logger.info(f"yt-dlp config: {ydl_opts}")

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
    """Background task to extract subtitles with retry logic"""
    max_retries = 3
    retry_delay = 10  # seconds

    for attempt in range(max_retries):
        try:
            task_store[task_id]["status"] = TaskStatus.PROCESSING
            task_store[task_id]["progress"] = 25 + (attempt * 20)  # Progress increases with attempts

            if attempt > 0:
                logger.info(f"Retry attempt {attempt + 1}/{max_retries} for task {task_id}")
                import time
                time.sleep(retry_delay)

            extractor = SubtitleExtractor()
            result = asyncio.run(extractor.extract(url, language_preference))

            if result["success"]:
                task_store[task_id]["status"] = TaskStatus.COMPLETED
                task_store[task_id]["content"] = result["content"]
                task_store[task_id]["language"] = result["language"]
                task_store[task_id]["title"] = result["title"]
                task_store[task_id]["progress"] = 100
                task_store[task_id]["message"] = f"Successfully extracted subtitles ({result['language']})"
                return  # Success, exit retry loop
            else:
                error_msg = result["error"]

                # If it's the last attempt, fail
                if attempt == max_retries - 1:
                    task_store[task_id]["status"] = TaskStatus.FAILED
                    task_store[task_id]["progress"] = 0

                    # Enhanced error messages
                    if "bot" in error_msg.lower() or "sign in" in error_msg.lower():
                        task_store[task_id]["message"] = f"YouTube 機器人檢測：{error_msg}。建議等待 5-10 分鐘後重試。"
                    elif "403" in error_msg or "forbidden" in error_msg.lower():
                        task_store[task_id]["message"] = f"訪問被拒：{error_msg}。可能是 IP 被暫時限制，請稍後重試。"
                    elif "no subtitles" in error_msg.lower():
                        task_store[task_id]["message"] = f"此影片沒有可用的字幕。"
                    else:
                        task_store[task_id]["message"] = error_msg
                    return
                else:
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}, retrying...")

        except Exception as e:
            logger.error(f"Task {task_id} attempt {attempt + 1} failed: {str(e)}")

            # If it's the last attempt, fail
            if attempt == max_retries - 1:
                task_store[task_id]["status"] = TaskStatus.FAILED
                task_store[task_id]["progress"] = 0
                task_store[task_id]["message"] = f"提取失敗（已重試 {max_retries} 次）: {str(e)}"
                return
            else:
                logger.warning(f"Retrying after error: {str(e)}")


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
