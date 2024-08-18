
class ProxyManager:
    def __init__(self, proxy: str = None):
        self.proxy = proxy

    async def get_proxy(self) -> str:
        return self.proxy
