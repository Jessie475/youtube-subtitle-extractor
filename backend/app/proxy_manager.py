"""
Proxy Manager for Webshare Free Proxies
Handles fetching and rotating through available proxies
"""
import requests
import random
import logging
import os
from typing import List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manage Webshare proxy list with caching and rotation"""

    def __init__(self):
        self.proxy_list: List[str] = []
        self.last_fetch: Optional[datetime] = None
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
        self.proxy_list_url = os.getenv(
            "WEBSHARE_PROXY_LIST_URL",
            ""
        )

    def _should_refresh(self) -> bool:
        """Check if proxy list should be refreshed"""
        if not self.proxy_list:
            return True
        if not self.last_fetch:
            return True
        if datetime.now() - self.last_fetch > self.cache_duration:
            return True
        return False

    def fetch_proxies(self) -> bool:
        """Fetch proxy list from Webshare API"""
        if not self.proxy_list_url:
            logger.warning("WEBSHARE_PROXY_LIST_URL not configured")
            return False

        try:
            logger.info("Fetching proxy list from Webshare...")
            response = requests.get(self.proxy_list_url, timeout=10)
            response.raise_for_status()

            proxy_lines = response.text.strip().split('\n')
            self.proxy_list = []

            for line in proxy_lines:
                if line.strip():
                    # Format: IP:PORT:USERNAME:PASSWORD
                    parts = line.strip().split(':')
                    if len(parts) == 4:
                        ip, port, username, password = parts
                        proxy_url = f"http://{username}:{password}@{ip}:{port}"
                        self.proxy_list.append(proxy_url)

            self.last_fetch = datetime.now()
            logger.info(f"✅ Loaded {len(self.proxy_list)} proxies from Webshare")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to fetch proxy list: {e}")
            return False

    def get_random_proxy(self) -> Optional[str]:
        """Get a random proxy from the list"""
        # Refresh if needed
        if self._should_refresh():
            self.fetch_proxies()

        if not self.proxy_list:
            return None

        proxy = random.choice(self.proxy_list)
        logger.info(f"🔀 Selected proxy: {proxy.split('@')[1] if '@' in proxy else proxy}")
        return proxy

    def get_multiple_proxies(self, count: int = 3) -> List[str]:
        """Get multiple random proxies for retry logic"""
        # Refresh if needed
        if self._should_refresh():
            self.fetch_proxies()

        if not self.proxy_list:
            return []

        # Return up to 'count' random proxies
        available_count = min(count, len(self.proxy_list))
        proxies = random.sample(self.proxy_list, available_count)

        logger.info(f"🔀 Selected {len(proxies)} proxies for rotation")
        return proxies

    def is_enabled(self) -> bool:
        """Check if proxy fallback is enabled"""
        return bool(self.proxy_list_url) and os.getenv("ENABLE_PROXY_FALLBACK", "false").lower() == "true"


# Global proxy manager instance
proxy_manager = ProxyManager()
