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


class SubtitleItem(BaseModel):
    content: str
    language: str
    is_auto_generated: bool = False


class SubtitleResponse(BaseModel):
    task_id: str
    status: TaskStatus
    subtitles: Optional[list[SubtitleItem]] = None
    message: str


class SubtitleExtractor:
    """Helper class to extract subtitles from YouTube videos using yt-dlp"""

    def __init__(self):
        self.preferred_languages = ["zh-TW", "zh-CN", "zh", "en"]

    async def extract(self, url: str, language_preference: Optional[list[str]] = None, proxy_url: Optional[str] = None) -> dict:
        """Extract subtitles from a YouTube video using yt-dlp - returns multiple languages if available"""
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
                "socket_timeout": 30,  # Reduced from 120s for faster failures
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

                # Extract multiple languages (Chinese and English)
                subtitle_list = self._get_multiple_subtitles(subtitles, automatic_captions)

                if subtitle_list:
                    logger.info(f"Successfully extracted {len(subtitle_list)} subtitle(s): {[s['language'] for s in subtitle_list]}")
                    return {
                        "success": True,
                        "subtitles": subtitle_list,
                        "title": info.get("title", "Unknown"),
                    }
                else:
                    return {"success": False, "error": "No subtitles found for this video"}

        except Exception as e:
            logger.error(f"Error extracting subtitles with yt-dlp: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_multiple_subtitles(self, subtitles: dict, automatic_captions: dict) -> list[dict]:
        """Extract multiple subtitle languages (Chinese and English if available)"""
        result = []
        extracted_base_langs = set()
        
        # Define language groups we want to extract
        chinese_langs = ["zh-TW", "zh-CN", "zh-Hans", "zh-Hant", "zh"]
        english_langs = ["en", "en-US", "en-GB"]
        
        # Priority 1: Manual subtitles (higher quality)
        for lang in chinese_langs:
            if lang in subtitles and "chinese" not in extracted_base_langs:
                subtitle_data = self._fetch_subtitle_content(subtitles[lang], lang, is_auto=False)
                if subtitle_data:
                    result.append(subtitle_data)
                    extracted_base_langs.add("chinese")
                    break
        
        for lang in english_langs:
            if lang in subtitles and "english" not in extracted_base_langs:
                subtitle_data = self._fetch_subtitle_content(subtitles[lang], lang, is_auto=False)
                if subtitle_data:
                    result.append(subtitle_data)
                    extracted_base_langs.add("english")
                    break
        
        # Priority 2: Auto-generated captions (if manual not available)
        if "chinese" not in extracted_base_langs:
            for lang in chinese_langs:
                if lang in automatic_captions:
                    subtitle_data = self._fetch_subtitle_content(automatic_captions[lang], lang, is_auto=True)
                    if subtitle_data:
                        result.append(subtitle_data)
                        extracted_base_langs.add("chinese")
                        break
        
        if "english" not in extracted_base_langs:
            for lang in english_langs:
                if lang in automatic_captions:
                    subtitle_data = self._fetch_subtitle_content(automatic_captions[lang], lang, is_auto=True)
                    if subtitle_data:
                        result.append(subtitle_data)
                        extracted_base_langs.add("english")
                        break
        
        # Priority 3: Fallback to any available subtitle
        if not result:
            # Try any manual subtitle first
            if subtitles:
                lang = list(subtitles.keys())[0]
                subtitle_data = self._fetch_subtitle_content(subtitles[lang], lang, is_auto=False)
                if subtitle_data:
                    result.append(subtitle_data)
            # Then try any auto-generated
            elif automatic_captions:
                lang = list(automatic_captions.keys())[0]
                subtitle_data = self._fetch_subtitle_content(automatic_captions[lang], lang, is_auto=True)
                if subtitle_data:
                    result.append(subtitle_data)
        
        return result

    def _get_best_subtitles(self, subtitles: dict, automatic_captions: dict) -> Optional[dict]:
        """Get the best available subtitles based on language preference (legacy method)"""
        # Check manual subtitles first
        for lang in self.preferred_languages:
            if lang in subtitles:
                return self._fetch_subtitle_content(subtitles[lang], lang, is_auto=False)

        # Check automatic captions
        for lang in self.preferred_languages:
            if lang in automatic_captions:
                return self._fetch_subtitle_content(automatic_captions[lang], lang, is_auto=True)

        # Use first available
        if subtitles:
            lang = list(subtitles.keys())[0]
            return self._fetch_subtitle_content(subtitles[lang], lang, is_auto=False)

        if automatic_captions:
            lang = list(automatic_captions.keys())[0]
            return self._fetch_subtitle_content(automatic_captions[lang], lang, is_auto=True)

        return None

    def _fetch_subtitle_content(self, subtitle_list: list, language: str, is_auto: bool = False) -> Optional[dict]:
        """Fetch and parse subtitle content"""
        try:
            if not subtitle_list:
                return None

            # JSON3 format
            if subtitle_list[0]["ext"] == "json3":
                response = requests.get(subtitle_list[0]["url"], timeout=8)  # Reduced from 10s
                data = response.json()
                text = ""
                for event in data.get("events", []):
                    if "segs" in event:
                        for seg in event["segs"]:
                            text += seg.get("utf8", "")
                
                # Add auto-generated indicator
                display_lang = f"{language} (自動生成)" if is_auto else language
                return {"text": text, "language": display_lang, "is_auto_generated": is_auto}

            # VTT or SRT format
            else:
                response = requests.get(subtitle_list[0]["url"], timeout=8)  # Reduced from 10s
                content = response.text
                lines = content.split("\n")
                subtitle_text = []
                for line in lines:
                    # Skip empty lines, timestamps, and sequence numbers
                    if line.strip() and "-->" not in line and not line.isdigit():
                        subtitle_text.append(line.strip())

                # Add auto-generated indicator
                display_lang = f"{language} (自動生成)" if is_auto else language
                return {"text": "\n".join(subtitle_text), "language": display_lang, "is_auto_generated": is_auto}

        except Exception as e:
            logger.error(f"Error fetching subtitle content: {e}")
            return None


def process_subtitle_extraction(task_id: str, url: str, language_preference: Optional[list[str]]):
    """Background task to extract subtitles using Webshare proxy rotation"""
    import time

    extractor = SubtitleExtractor()
    task_store[task_id]["status"] = TaskStatus.PROCESSING
    task_store[task_id]["progress"] = 10

    # Check if proxy is enabled
    if not proxy_manager.is_enabled():
        logger.error("Proxy is not enabled. Cannot extract subtitles without proxy in production.")
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["progress"] = 0
        task_store[task_id]["message"] = "代理服務未啟用，無法提取字幕。請聯繫管理員。"
        return

    # Get proxies for rotation (try up to 5 proxies)
    proxies = proxy_manager.get_multiple_proxies(count=5)

    if not proxies:
        logger.error("No proxies available")
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["progress"] = 0
        task_store[task_id]["message"] = "沒有可用的代理服務。請聯繫管理員。"
        return

    logger.info(f"Starting extraction with {len(proxies)} proxies")

    # Try each proxy until success
    for i, proxy_url in enumerate(proxies):
        logger.info(f"Attempt {i + 1}/{len(proxies)}: Using proxy {i + 1}")
        task_store[task_id]["progress"] = 20 + (i * 15)

        if i > 0:
            time.sleep(1)  # Reduced from 3s for faster proxy rotation

        result = asyncio.run(extractor.extract(url, language_preference, proxy_url=proxy_url))

        if result["success"]:
            task_store[task_id]["status"] = TaskStatus.COMPLETED
            task_store[task_id]["subtitles"] = result["subtitles"]
            task_store[task_id]["title"] = result["title"]
            task_store[task_id]["progress"] = 100
            
            # Create message with all languages
            languages = [s["language"] for s in result["subtitles"]]
            lang_str = "、".join(languages)
            task_store[task_id]["message"] = f"成功提取 {len(result['subtitles'])} 個字幕 ({lang_str})"
            logger.info(f"✅ Success with proxy {i + 1}/{len(proxies)}")
            return
        else:
            error_msg = result.get('error', 'Unknown')
            logger.warning(f"Proxy {i + 1} failed: {error_msg[:100]}")

    # All proxies failed
    task_store[task_id]["status"] = TaskStatus.FAILED
    task_store[task_id]["progress"] = 0

    # Get last error message
    error_msg = result.get("error", "Unknown error")

    # Enhanced error messages
    if "bot" in error_msg.lower() or "sign in" in error_msg.lower():
        task_store[task_id]["message"] = f"YouTube 機器人檢測：所有代理都被封鎖。建議等待 5-10 分鐘後重試。"
    elif "403" in error_msg or "forbidden" in error_msg.lower():
        task_store[task_id]["message"] = f"訪問被拒：{error_msg[:200]}。所有代理都無法訪問，請稍後重試。"
    elif "no subtitles" in error_msg.lower():
        task_store[task_id]["message"] = f"此影片沒有可用的字幕。"
    else:
        task_store[task_id]["message"] = f"提取失敗（已嘗試 {len(proxies)} 個代理）: {error_msg[:200]}"


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
        "subtitles": None,
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

    # Convert subtitles to SubtitleItem list
    subtitle_items = [
        SubtitleItem(
            content=s["text"],
            language=s["language"],
            is_auto_generated=s.get("is_auto_generated", False)
        )
        for s in task["subtitles"]
    ]

    return SubtitleResponse(
        task_id=task_id,
        status=task["status"],
        subtitles=subtitle_items,
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
