import os
import httpx


OLGA_API_BASE = os.getenv("OLGA_API_BASE", "http://localhost:9091")


class OlgaClient:
    @staticmethod
    async def get_form_by_id(form_id: str) -> dict:
        url = f"{OLGA_API_BASE}/forms/getFromID/{form_id}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        
