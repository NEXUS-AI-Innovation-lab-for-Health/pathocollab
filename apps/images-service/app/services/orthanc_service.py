import os
import requests
from requests.auth import HTTPBasicAuth
from typing import Any, Dict, Optional


class OrthancService:
    def __init__(self):
        self.base_url = os.getenv("ORTHANC_URL", "http://orthanc:8042").rstrip("/")
        self.username = os.getenv("ORTHANC_USERNAME", "orthanc")
        self.password = os.getenv("ORTHANC_PASSWORD", "orthanc")
        self.timeout = int(os.getenv("ORTHANC_TIMEOUT", "60"))

    def _auth(self):
        if self.username:
            return HTTPBasicAuth(self.username, self.password)
        return None

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def get_json(self, path: str) -> Dict[str, Any]:
        url = self._url(path)
        r = requests.get(
            url,
            auth=self._auth(),
            timeout=self.timeout,
        )
        if not r.ok:
            raise RuntimeError(f"Orthanc GET {url} failed with {r.status_code}: {r.text}")
        return r.json()

    def get_bytes(self, path: str) -> bytes:
        url = self._url(path)
        r = requests.get(
            url,
            auth=self._auth(),
            timeout=self.timeout,
        )
        if not r.ok:
            raise RuntimeError(f"Orthanc GET {url} failed with {r.status_code}: {r.text}")
        return r.content

    def get_stream(self, path: str):
        url = self._url(path)
        r = requests.get(
            url,
            auth=self._auth(),
            timeout=self.timeout,
            stream=True,
        )
        if not r.ok:
            raise RuntimeError(f"Orthanc GET {url} failed with {r.status_code}: {r.text}")
        return r

    def post_bytes(self, path: str, data: bytes, content_type: str = "application/dicom") -> Dict[str, Any]:
        url = self._url(path)
        r = requests.post(
            url,
            auth=self._auth(),
            timeout=self.timeout,
            data=data,
            headers={"Content-Type": content_type},
        )
        if not r.ok:
            raise RuntimeError(f"Orthanc POST {url} failed with {r.status_code}: {r.text}")
        return r.json()

    def store_instance(self, dicom_bytes: bytes) -> Dict[str, Any]:
        return self.post_bytes("/instances", dicom_bytes, "application/dicom")

    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        return self.get_json(f"/instances/{instance_id}")

    def get_series(self, series_id: str) -> Dict[str, Any]:
        return self.get_json(f"/series/{series_id}")

    def get_study(self, study_id: str) -> Dict[str, Any]:
        return self.get_json(f"/studies/{study_id}")

    def get_patient(self, patient_id: str) -> Dict[str, Any]:
        return self.get_json(f"/patients/{patient_id}")

    def get_instance_preview(self, instance_id: str):
        return self.get_stream(f"/instances/{instance_id}/preview")

    def get_instance_file(self, instance_id: str):
        return self.get_stream(f"/instances/{instance_id}/file")

    @staticmethod
    def extract_id_from_store_reply(reply: Dict[str, Any]) -> Optional[str]:
        if "ID" in reply and reply["ID"]:
            return reply["ID"]

        path = reply.get("Path")
        if path and "/" in path:
            return path.rstrip("/").split("/")[-1]

        return None