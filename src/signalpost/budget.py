import asyncio
from typing import Dict, Any

class BudgetExceededException(Exception):
    pass

class ExecutionBudgetTracker:
    def __init__(self, max_requests: int = 2000, max_cost_usd: float = 10.00):
        self.max_requests = max_requests
        self.max_cost_usd = max_cost_usd
        self._request_count = 0
        self._cost_accrued = 0.0
        self._lock = asyncio.Lock()

    async def record_request(self, count: int = 1) -> None:
        async with self._lock:
            if self._request_count + count > self.max_requests:
                raise BudgetExceededException(
                    f"Outbound requests hard ceiling reached: {self._request_count}/{self.max_requests}"
                )
            self._request_count += count

    async def record_cost(self, cost: float) -> None:
        async with self._lock:
            if self._cost_accrued + cost > self.max_cost_usd:
                raise BudgetExceededException(
                    f"Cost budget reached: ${self._cost_accrued:.2f}/${self.max_cost_usd:.2f}"
                )
            self._cost_accrued += cost

    async def snapshot(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                "requests_used": self._request_count,
                "cost_usd": round(self._cost_accrued, 4),
                "remaining_requests": self.max_requests - self._request_count,
                "remaining_cost": round(self.max_cost_usd - self._cost_accrued, 4)
            }

print("budget.py created successfully!")
