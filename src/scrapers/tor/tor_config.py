from dataclasses import dataclass
from typing import List

@dataclass
class TorConfig:
    """Configuration for Tor connection and scraping"""
    socks_port: int = 9050
    control_port: int = 9051
    debug: bool = False
    max_retries: int = 3
    timeout: int = 30
    circuit_timeout: int = 10
    auto_renew_circuit: bool = True
    verify_connection: bool = True
    user_agents: List[str] = None
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0',
                'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
                'Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0',
            ]