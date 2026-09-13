import httpx
from typing import Optional, Dict
from signalpost.budget import ExecutionBudgetTracker

class ResilientHttpClient:
    def __init__(self, budget_tracker: ExecutionBudgetTracker, user_agent: str, timeout: float = 12.0):
        self.tracker = budget_tracker
        self.client = httpx.AsyncClient(
            headers={"User-Agent": user_agent, "Accept": "application/json, text/html"},
            timeout=timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        await self.tracker.record_request(1)
        resp = await self.client.get(url, headers=headers)
        resp.raise_for_status()
        return resp

    async def aclose(self):
        await self.client.aclose()
