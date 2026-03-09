from __future__ import annotations

import os
from typing import Any

import httpx


class OlgaClientError(Exception):
    pass


class OlgaClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLGA_API_URL", "http://localhost:9091").rstrip("/")
        self.timeout = float(os.getenv("OLGA_TIMEOUT", "30"))
        self.api_key = os.getenv("OLGA_API_KEY")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, json=json_body, headers=self._headers())

        if response.status_code >= 400:
            raise OlgaClientError(f"Olga API error {response.status_code}: {response.text}")

        if not response.content:
            return None
        return response.json()

    async def create_session(self, workflow_code: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/sessions",
            {"workflowCode": workflow_code, "data": data or {}},
        )

    async def get_session(self, session_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/sessions/{session_id}")

    async def get_tasks(self, session_id: str) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/api/sessions/{session_id}/tasks")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            return data["items"]
        return []

    async def complete_task(self, task_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/api/tasks/{task_id}/complete", data)
