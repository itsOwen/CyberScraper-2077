import requests
import random
import logging
import socket
import socks
from typing import Dict, Optional
from urllib.parse import urlparse
from .tor_config import TorConfig
from .exceptions import (
    TorConnectionError, 
    TorInitializationError, 
    OnionServiceError,
    TorProxyError
)

class TorManager:
    """Manages Tor connection and session handling"""
    
    def __init__(self, config: TorConfig = TorConfig()):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.config = config
        self._setup_logging()
        self._setup_proxy()
        
    def _setup_logging(self):
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
    def _setup_proxy(self):
        """Configure SOCKS proxy for Tor"""
        try:
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", self.config.socks_port)
            socket.socket = socks.socksocket
            self.proxies = {
                'http': f'socks5h://127.0.0.1:{self.config.socks_port}',
                'https': f'socks5h://127.0.0.1:{self.config.socks_port}'
            }
        except Exception as e:
            raise TorProxyError(f"Failed to setup Tor proxy: {str(e)}")

    def get_headers(self) -> Dict[str, str]:
        """Get randomized Tor Browser-like headers"""
        return {
            'User-Agent': random.choice(self.config.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }

    async def verify_tor_connection(self) -> bool:
        """Verify Tor connection is working"""
        try:
            session = self.get_tor_session()
            response = session.get('https://check.torproject.org/api/ip', 
                                 timeout=self.config.timeout)
            is_tor = response.json().get('IsTor', False)
            
            if is_tor:
                self.logger.info("Successfully connected to Tor network")
                return True
            else:
                raise TorConnectionError("Connection is not using Tor network")
                
        except Exception as e:
            raise TorConnectionError(f"Failed to verify Tor connection: {str(e)}")

    def get_tor_session(self) -> requests.Session:
        """Create a requests session that routes through Tor"""
        session = requests.Session()
        session.proxies = self.proxies
        session.headers = self.get_headers()
        return session

    @staticmethod
    def is_onion_url(url: str) -> bool:
        """Check if the given URL is an onion service"""
        try:
            parsed = urlparse(url)
            return parsed.hostname.endswith('.onion') if parsed.hostname else False
        except Exception:
            return False

    async def fetch_content(self, url: str) -> str:
        """Fetch content from an onion site"""
        if not self.is_onion_url(url):
            raise OnionServiceError("URL is not a valid onion service")

        try:
            session = self.get_tor_session()
            
            if self.config.verify_connection:
                await self.verify_tor_connection()
            
            response = session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            
            self.logger.info(f"Successfully fetched content from {url}")
            return response.text
            
        except requests.RequestException as e:
            raise OnionServiceError(f"Failed to fetch onion content: {str(e)}")
        except Exception as e:
            raise TorException(f"Unexpected error fetching onion content: {str(e)}")