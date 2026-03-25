from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from typing import List
from datetime import datetime, timezone
import os
import uuid

from app.models.radiology import RadiologySeriesLinkDB, RadiologySeriesSummary
from app.services.minio_service import MinioService
from app.services.orthanc_service import OrthancService


router = APIRouter(prefix="/radiology", tags=["Radiology"])

minio_service = MinioService()
orthanc_service = OrthancService()


def get_db_override():
    raise RuntimeError("get_db not injected")


def router_api():
    return router


def _safe_tag(d: dict, key: str, default=None):
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def _series_to_summary(row: RadiologySeriesLinkDB) -> RadiologySeriesSummary:
    return RadiologySeriesSummary.model_validate(row)


@router.post("/upload-raw", status_code=201)
async def upload_radiology_raw(
    patient_id: str,
    file: UploadFile = File(...),
):
    """
    Upload simple d'un DICOM dans MinIO (niveau patient).

    Chemin :
    patients/{patient_id}/radiology/raw/{uuid}_{filename}.dcm
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    radiology_id = str(uuid.uuid4())

    original_name = file.filename or "image.dcm"
    safe_name = os.path.basename(original_name)

    if not safe_name.lower().endswith(".dcm"):
        safe_name = f"{safe_name}.dcm"

    object_name = (
        f"patients/{patient_id}/radiology/raw/"
        f"{radiology_id}_{safe_name}"
    )

    minio_service.upload_file(
        content,
        object_name,
        file.content_type or "application/dicom",
    )

    return {
        "radiology_id": radiology_id,
        "patient_id": patient_id,
        "object_name": object_name,
        "filename": safe_name,
        "content_type": file.content_type or "application/dicom",
        "size": len(content),
        "message": "Radiology image uploaded successfully",
    }


@router.post("/upload-raw-batch", status_code=201)
async def upload_radiology_raw_batch(
    patient_id: str,
    files: List[UploadFile] = File(...),
):
    """
    Upload multiple DICOM files dans MinIO uniquement (niveau patient).
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    uploaded = []

    for file in files:
        content = await file.read()
        if not content:
            continue

        radiology_id = str(uuid.uuid4())

        original_name = file.filename or "image.dcm"
        safe_name = os.path.basename(original_name)

        if not safe_name.lower().endswith(".dcm"):
            safe_name = f"{safe_name}.dcm"

        object_name = (
            f"patients/{patient_id}/radiology/raw/"
            f"{radiology_id}_{safe_name}"
        )

        minio_service.upload_file(
            content,
            object_name,
            file.content_type or "application/dicom",
        )

        uploaded.append({
            "radiology_id": radiology_id,
            "patient_id": patient_id,
            "object_name": object_name,
            "filename": safe_name,
            "size": len(content),
        })

    if not uploaded:
        raise HTTPException(status_code=400, detail="All uploaded files were empty")

    return {
        "count": len(uploaded),
        "items": uploaded,
        "message": "Radiology raw images uploaded successfully",
    }


@router.post("/upload", status_code=201)
async def upload_radiology_dicoms(
    patient_id: str,
    uploaded_by: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db_override),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    uploaded = []

    for file in files:
        content = await file.read()
        if not content:
            continue

        object_id = str(uuid.uuid4())

        original_name = file.filename or "image.dcm"
        safe_name = os.path.basename(original_name)
        if not safe_name.lower().endswith(".dcm"):
            safe_name = f"{safe_name}.dcm"

        minio_path = f"patients/{patient_id}/radiology/raw/{object_id}_{safe_name}"

        # 1) archive brute dans MinIO
        try:
            minio_service.upload_file(
                content,
                minio_path,
                file.content_type or "application/dicom",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"MinIO upload failed: {str(e)}")

        # 2) push vers Orthanc
        try:
            store_reply = orthanc_service.store_instance(content)
            print(f"[RADIOLOGY] store_reply={store_reply}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Orthanc store failed: {str(e)}")

        instance_id = orthanc_service.extract_id_from_store_reply(store_reply)
        if not instance_id:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to resolve Orthanc instance ID from reply: {store_reply}"
            )

        try:
            instance = orthanc_service.get_instance(instance_id)
            print(f"[RADIOLOGY] instance={instance}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Orthanc instance fetch failed: {str(e)}")

        orthanc_series_id = store_reply.get("ParentSeries") or instance.get("ParentSeries")
        orthanc_study_id = store_reply.get("ParentStudy") or instance.get("ParentStudy")
        orthanc_patient_id = store_reply.get("ParentPatient") or instance.get("ParentPatient")

        if not orthanc_series_id or not orthanc_study_id or not orthanc_patient_id:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Orthanc hierarchy incomplete after upload. "
                    f"store_reply={store_reply}, instance={instance}"
                ),
            )
        
        try:
            series = orthanc_service.get_series(orthanc_series_id)
            study = orthanc_service.get_study(orthanc_study_id)
            patient = orthanc_service.get_patient(orthanc_patient_id)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Orthanc hierarchy fetch failed: {str(e)}")

        series_main = series.get("MainDicomTags", {}) or {}
        study_main = study.get("MainDicomTags", {}) or {}
        patient_main = patient.get("MainDicomTags", {}) or {}

        instances = series.get("Instances", []) or []
        preview_instance_id = instances[0] if instances else instance_id

        try:
            result = await db.execute(
                select(RadiologySeriesLinkDB).where(
                    and_(
                        RadiologySeriesLinkDB.app_patient_id == patient_id,
                        RadiologySeriesLinkDB.orthanc_series_id == orthanc_series_id,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            raw_prefix = f"patients/{patient_id}/radiology/raw/"

            if existing:
                existing.preview_instance_id = preview_instance_id
                existing.patient_name = _safe_tag(patient_main, "PatientName")
                existing.dicom_patient_id = _safe_tag(patient_main, "PatientID")
                existing.study_instance_uid = _safe_tag(study_main, "StudyInstanceUID")
                existing.series_instance_uid = _safe_tag(series_main, "SeriesInstanceUID")
                existing.modality = _safe_tag(series_main, "Modality")
                existing.study_date = _safe_tag(study_main, "StudyDate")
                existing.study_description = _safe_tag(study_main, "StudyDescription")
                existing.series_description = _safe_tag(series_main, "SeriesDescription")
                existing.instances_count = len(instances)
                existing.raw_minio_prefix = raw_prefix
                existing.uploaded_by = uploaded_by
                existing.updated_at = datetime.now(timezone.utc)
                row = existing
            else:
                row = RadiologySeriesLinkDB(
                    app_patient_id=patient_id,
                    uploaded_by=uploaded_by,
                    orthanc_patient_id=orthanc_patient_id,
                    orthanc_study_id=orthanc_study_id,
                    orthanc_series_id=orthanc_series_id,
                    preview_instance_id=preview_instance_id,
                    patient_name=_safe_tag(patient_main, "PatientName"),
                    dicom_patient_id=_safe_tag(patient_main, "PatientID"),
                    study_instance_uid=_safe_tag(study_main, "StudyInstanceUID"),
                    series_instance_uid=_safe_tag(series_main, "SeriesInstanceUID"),
                    modality=_safe_tag(series_main, "Modality"),
                    study_date=_safe_tag(study_main, "StudyDate"),
                    study_description=_safe_tag(study_main, "StudyDescription"),
                    series_description=_safe_tag(series_main, "SeriesDescription"),
                    instances_count=len(instances),
                    raw_minio_prefix=raw_prefix,
                )
                db.add(row)

            await db.commit()
            await db.refresh(row)

        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Radiology DB save failed: {str(e)}")

        uploaded.append({
            "filename": safe_name,
            "minio_path": minio_path,
            "instance_id": instance_id,
            "orthanc_series_id": orthanc_series_id,
            "orthanc_study_id": orthanc_study_id,
            "orthanc_patient_id": orthanc_patient_id,
            "series_description": row.series_description,
            "modality": row.modality,
        })

    if not uploaded:
        raise HTTPException(status_code=400, detail="All uploaded files were empty")

    return {
        "message": "Radiology DICOM uploaded successfully",
        "count": len(uploaded),
        "items": uploaded,
    }


@router.get("/patients/{patient_id}/raw")
def list_radiology_raw(patient_id: str):
    """
    Liste les DICOM stockés dans MinIO pour un patient.
    """
    prefix = f"patients/{patient_id}/radiology/raw/"
    objects = minio_service.list_objects(prefix)

    results = []
    for obj in objects:
        object_name = obj["object_name"]
        results.append({
            "object_name": object_name,
            "size": obj.get("size"),
            "last_modified": obj.get("last_modified"),
            "etag": obj.get("etag"),
            "url": f"/api/radiology/raw/file?object_name={object_name}",
        })

    return {
        "patient_id": patient_id,
        "count": len(results),
        "items": results,
    }


@router.get("/raw/file")
def get_radiology_raw_file(object_name: str):
    """
    Stream d'un DICOM depuis MinIO
    """
    try:
        response = minio_service.get_object(object_name)

        def stream():
            for chunk in response.stream(32 * 1024):
                yield chunk

        return StreamingResponse(
            stream(),
            media_type="application/dicom",
            headers={
                "Content-Disposition": f'inline; filename="{os.path.basename(object_name)}"'
            },
        )

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/patients/{patient_id}/series", response_model=List[RadiologySeriesSummary])
async def list_patient_radiology_series(
    patient_id: str,
    db: AsyncSession = Depends(get_db_override),
):
    result = await db.execute(
        select(RadiologySeriesLinkDB)
        .where(RadiologySeriesLinkDB.app_patient_id == patient_id)
        .order_by(RadiologySeriesLinkDB.created_at.desc())
    )
    rows = result.scalars().all()
    return [_series_to_summary(r) for r in rows]


@router.get("/series/{orthanc_series_id}")
def get_radiology_series_detail(orthanc_series_id: str):
    try:
        series = orthanc_service.get_series(orthanc_series_id)
        study_id = series.get("ParentStudy")
        patient_id = series.get("ParentPatient")

        study = orthanc_service.get_study(study_id) if study_id else {}
        patient = orthanc_service.get_patient(patient_id) if patient_id else {}

        return {
            "series": series,
            "study": study,
            "patient": patient,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orthanc series fetch failed: {str(e)}")


@router.get("/series/{orthanc_series_id}/instances")
def list_series_instances(orthanc_series_id: str):
    try:
        series = orthanc_service.get_series(orthanc_series_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orthanc series fetch failed: {str(e)}")

    instance_ids = series.get("Instances", []) or []
    items = []

    for iid in instance_ids:
        try:
            inst = orthanc_service.get_instance(iid)
            tags = inst.get("MainDicomTags", {}) or {}
            index_in_series = inst.get("IndexInSeries")
            number = tags.get("InstanceNumber")
            items.append({
                "instance_id": iid,
                "instance_number": number,
                "index_in_series": index_in_series,
                "sop_instance_uid": tags.get("SOPInstanceUID"),
                "preview_url": f"/api/radiology/instances/{iid}/preview",
                "file_url": f"/api/radiology/instances/{iid}/file",
            })
        except Exception:
            items.append({
                "instance_id": iid,
                "instance_number": None,
                "index_in_series": None,
                "sop_instance_uid": None,
                "preview_url": f"/api/radiology/instances/{iid}/preview",
                "file_url": f"/api/radiology/instances/{iid}/file",
            })

    def _sort_key(x):
        n = x.get("instance_number")
        idx = x.get("index_in_series")
        if isinstance(n, str) and n.isdigit():
            n = int(n)
        if n is None:
            n = 10**9
        if idx is None:
            idx = 10**9
        return (n, idx)

    items.sort(key=_sort_key)

    return {
        "series_id": orthanc_series_id,
        "count": len(items),
        "instances": items,
    }


@router.get("/instances/{instance_id}/preview")
def get_instance_preview(instance_id: str):
    try:
        r = orthanc_service.get_instance_preview(instance_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orthanc preview failed: {str(e)}")

    media_type = r.headers.get("Content-Type", "image/jpeg")

    def iterfile():
        try:
            for chunk in r.iter_content(chunk_size=32 * 1024):
                if chunk:
                    yield chunk
        finally:
            r.close()

    return StreamingResponse(iterfile(), media_type=media_type)


@router.get("/instances/{instance_id}/file")
def get_instance_file(instance_id: str):
    try:
        r = orthanc_service.get_instance_file(instance_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orthanc file fetch failed: {str(e)}")

    media_type = r.headers.get("Content-Type", "application/dicom")

    def iterfile():
        try:
            for chunk in r.iter_content(chunk_size=32 * 1024):
                if chunk:
                    yield chunk
        finally:
            r.close()

    return StreamingResponse(
        iterfile(),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{instance_id}.dcm"'},
    )