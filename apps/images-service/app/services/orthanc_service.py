import os
from typing import Any, Dict, Optional

import requests
from requests import Session
from requests.auth import HTTPBasicAuth


class OrthancService:
    def __init__(self):
        self.base_url = os.getenv("ORTHANC_URL", "http://orthanc:8042").rstrip("/")
        self.username = os.getenv("ORTHANC_USERNAME", "orthanc")
        self.password = os.getenv("ORTHANC_PASSWORD", "orthanc")
        self.timeout = float(os.getenv("ORTHANC_TIMEOUT", "3"))
        self.enabled = os.getenv("ORTHANC_ENABLED", "true").lower() == "true"
        self.session: Session = requests.Session()

    def _auth(self):
        if self.username:
            return HTTPBasicAuth(self.username, self.password)
        return None

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs):
        if not self.enabled:
            raise RuntimeError("Orthanc is disabled")
        url = self._url(path)
        response = self.session.request(
            method=method,
            url=url,
            auth=self._auth(),
            timeout=kwargs.pop("timeout", self.timeout),
            **kwargs,
        )
        if not response.ok:
            raise RuntimeError(
                f"Orthanc {method.upper()} {url} failed with {response.status_code}: {response.text}"
            )
        return response
    
    def is_available(self) -> bool:
        if not self.enabled:
            return False

        try:
            response = self.session.get(
                self._url("/system"),
                auth=self._auth(),
                timeout=2,
            )
            return response.ok
        except Exception:
            return False

    def get_json(self, path: str) -> Dict[str, Any]:
        return self._request("GET", path).json()

    def get_bytes(self, path: str) -> bytes:
        return self._request("GET", path).content

    def get_stream(self, path: str):
        return self._request("GET", path, stream=True)

    def post_bytes(
        self,
        path: str,
        data: bytes,
        content_type: str = "application/dicom",
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            path,
            data=data,
            headers={"Content-Type": content_type},
        ).json()

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

    def get_instance_tags(self, instance_id: str, simplify: bool = True) -> Dict[str, Any]:
        path = f"/instances/{instance_id}/tags"
        if simplify:
            path += "?simplify"
        return self.get_json(path)

    def get_instance_header(self, instance_id: str) -> Dict[str, Any]:
        instance = self.get_instance(instance_id)
        tags = self.get_instance_tags(instance_id, simplify=True)
        return {
            "instance_id": instance_id,
            "parent_series": instance.get("ParentSeries"),
            "parent_study": instance.get("ParentStudy"),
            "parent_patient": instance.get("ParentPatient"),
            "index_in_series": instance.get("IndexInSeries"),
            "main_dicom_tags": instance.get("MainDicomTags", {}) or {},
            "simplified_tags": tags or {},
        }

    @staticmethod
    def extract_id_from_store_reply(reply: Dict[str, Any]) -> Optional[str]:
        if "ID" in reply and reply["ID"]:
            return reply["ID"]

        path = reply.get("Path")
        if path and "/" in path:
            return path.rstrip("/").split("/")[-1]

        return None
