"""
Test script for YouTube Transcript API
"""
import asyncio
import sys
import os

# Add parent directory to path to import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import SubtitleExtractor


async def test_extract():
    """Test subtitle extraction with a known video"""

    # Test with a popular video that should have subtitles
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up
        "https://youtu.be/dQw4w9WgXcQ",  # Short URL format
    ]

    extractor = SubtitleExtractor()

    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing URL: {url}")
        print('='*60)

        result = await extractor.extract(url, language_preference=["en", "zh-TW", "zh-CN"])

        if result["success"]:
            print(f"✓ Success!")
            print(f"  Language: {result['language']}")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  Content length: {len(result['content'])} characters")
            print(f"  First 200 characters: {result['content'][:200]}...")
        else:
            print(f"✗ Failed!")
            print(f"  Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(test_extract())
