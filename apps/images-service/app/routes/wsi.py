import os
import shutil
import subprocess
import tempfile
import uuid
import asyncio
from pathlib import Path
from typing import List, Tuple

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import Response, FileResponse

from app.services.minio_service import MinioService

router = APIRouter(prefix="/wsi", tags=["WSI"])
minio = MinioService()


def _guess_mime(path: str) -> str:
    if path.endswith(".dzi"):
        return "application/xml"
    if path.endswith(".jpg") or path.endswith(".jpeg"):
        return "image/jpeg"
    if path.endswith(".png"):
        return "image/png"
    return "application/octet-stream"


@router.post("/upload", status_code=201)
async def upload_wsi(patient_id: str, file: UploadFile = File(...)):
    wsi_id = str(uuid.uuid4())
    object_name = f"patients/{patient_id}/raw/wsi/{wsi_id}/{file.filename}"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    minio.upload_file(
        content,
        object_name,
        file.content_type or "application/octet-stream",
    )

    return {
        "wsi_id": wsi_id,
        "patient_id": patient_id,
        "object_name": object_name,
        "filename": file.filename,
    }


async def _upload_tile_batch(tile_files: List[Tuple[str, str]], patient_id: str, wsi_id: str):
    semaphore = asyncio.Semaphore(8)

    async def upload_one(local_path: str, rel_path: str):
        async with semaphore:
            object_name = f"patients/{patient_id}/dzi/{wsi_id}/slide_files/{rel_path.replace(os.sep, '/')}"
            await asyncio.to_thread(
                minio.upload_path,
                local_path,
                object_name,
                "image/jpeg",
            )

    await asyncio.gather(*(upload_one(local, rel) for local, rel in tile_files))


@router.post("/{wsi_id}/convert-dzi", status_code=202)
async def convert_wsi_to_dzi(
    wsi_id: str,
    patient_id: str,
    object_name: str,
    background_tasks: BackgroundTasks,
):
    async def _convert_and_upload():
        try:
            print("=== DZI Conversion Started ===")

            vips_path = shutil.which("vips")
            if not vips_path:
                raise RuntimeError(
                    "VIPS is not installed in the images-service container. "
                    "Install libvips-tools and rebuild the image."
                )

            with tempfile.TemporaryDirectory() as tmp:
                input_name = os.path.basename(object_name)
                in_path = os.path.join(tmp, input_name)
                out_base = os.path.join(tmp, "slide")

                data = await asyncio.to_thread(minio.get_object_bytes, object_name)
                if data is None:
                    raise FileNotFoundError(f"WSI object not found in MinIO: {object_name}")

                with open(in_path, "wb") as f:
                    f.write(data)

                cmd = [
                    vips_path,
                    "dzsave",
                    in_path,
                    out_base,
                    "--layout=dz",
                    "--suffix=.jpg[Q=75]",
                    "--tile-size=512",
                    "--overlap=0",
                    "--depth=onepixel",
                ]

                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )

                if result.returncode != 0:
                    raise RuntimeError(result.stderr or f"vips failed with code {result.returncode}")

                dzi_path = out_base + ".dzi"
                files_dir = out_base + "_files"

                if not os.path.exists(dzi_path):
                    raise RuntimeError("DZI file not generated")
                if not os.path.isdir(files_dir):
                    raise RuntimeError("Tiles directory not generated")

                dzi_object = f"patients/{patient_id}/dzi/{wsi_id}/slide.dzi"
                await asyncio.to_thread(minio.upload_path, dzi_path, dzi_object, "application/xml")

                tile_files: List[Tuple[str, str]] = []
                for root, _, filenames in os.walk(files_dir):
                    for name in filenames:
                        local_path = os.path.join(root, name)
                        rel_path = os.path.relpath(local_path, files_dir)
                        tile_files.append((local_path, rel_path))

                if not tile_files:
                    raise RuntimeError("No DZI tiles generated")

                batch_size = 200
                for i in range(0, len(tile_files), batch_size):
                    batch = tile_files[i:i + batch_size]
                    await _upload_tile_batch(batch, patient_id, wsi_id)

                print("=== DZI Conversion Completed Successfully ===")
                print(f"Uploaded {len(tile_files)} tiles for WSI {wsi_id}")

        except Exception as e:
            print("=== DZI Conversion Failed ===")
            print(str(e))

    background_tasks.add_task(_convert_and_upload)

    return {
        "message": "DZI conversion started",
        "wsi_id": wsi_id,
        "patient_id": patient_id,
        "object_name": object_name,
        "status": "processing",
    }


@router.get("/patients/{patient_id}/{wsi_id}/dzi")
def get_dzi(patient_id: str, wsi_id: str):
    obj = f"patients/{patient_id}/dzi/{wsi_id}/slide.dzi"
    data = minio.get_object_bytes(obj)
    if data is None:
        raise HTTPException(status_code=404, detail=f"DZI not found: {obj}")

    return Response(
        content=data,
        media_type="application/xml",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/patients/{patient_id}/{wsi_id}/slide_files/{path:path}")
def get_tile(patient_id: str, wsi_id: str, path: str):
    obj = f"patients/{patient_id}/dzi/{wsi_id}/slide_files/{path}"
    data = minio.get_object_bytes(obj)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Tile not found: {obj}")
    
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/openseadragon-images/{file_name}")
def get_openseadragon_image(file_name: str):
    frontend_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "frontend"
        / "node_modules"
        / "openseadragon"
        / "build"
        / "openseadragon"
        / "images"
    )
    image_path = frontend_path / file_name

    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"OpenSeadragon image not found: {file_name}")

    return FileResponse(image_path)


@router.get("/patients/{patient_id}/{wsi_id}/dzi_files/{path:path}")
def get_tile_alias(patient_id: str, wsi_id: str, path: str):
    obj = f"patients/{patient_id}/dzi/{wsi_id}/slide_files/{path}"
    data = minio.get_object_bytes(obj)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Tile not found: {obj}")
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )