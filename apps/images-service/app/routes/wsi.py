import os
import shutil
import subprocess
import tempfile
import uuid
import asyncio
import concurrent.futures
from pathlib import Path
from typing import List
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
    # S'assurer que le content_type est correct
    content_type = file.content_type or "application/octet-stream"
    
    # Vérifier que content n'est pas vide
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")
    
    minio.upload_file(content, object_name, content_type)

    return {"wsi_id": wsi_id, "patient_id": patient_id, "object_name": object_name, "filename": file.filename}

async def _upload_tile_batch(tile_files: List[tuple], patient_id: str, wsi_id: str):
    """Upload un lot de tiles en parallèle"""
    def upload_single_tile(local_path: str, rel_path: str):
        tile_object = f"patients/{patient_id}/dzi/{wsi_id}/slide_files/{rel_path.replace(os.sep, '/')}"
        with open(local_path, "rb") as f:
            minio.upload_file(f.read(), tile_object, "image/jpeg")
    
    # Exécuter les uploads en parallèle (max 10 à la fois)
    semaphore = asyncio.Semaphore(10)
    async def upload_with_semaphore(local_path, rel_path):
        async with semaphore:
            return await asyncio.get_event_loop().run_in_executor(
                None, upload_single_tile, local_path, rel_path
            )
    
    tasks = [upload_with_semaphore(local_path, rel_path) for local_path, rel_path in tile_files]
    await asyncio.gather(*tasks)

@router.post("/{wsi_id}/convert-dzi", status_code=202)
async def convert_wsi_to_dzi(wsi_id: str, patient_id: str, object_name: str, background_tasks: BackgroundTasks):
    """
    object_name = chemin MinIO du WSI original (ex: wsi/<wsi_id}/slide.svs)
    Version optimisée avec traitement asynchrone et parallélisation
    """
    
    async def _convert_and_upload():
        try:
            print("=== DZI Conversion Started ===")
            
            # Vérifier d'abord si vips est disponible
            vips_path = "vips"
            
            try:
                import subprocess
                result = subprocess.run([vips_path, "--version"], capture_output=True, text=True, timeout=30)
                print(f"VIPS version: {result.stdout.strip()}")
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                if isinstance(e, subprocess.TimeoutExpired):
                    print(f"VIPS timeout after 30s, trying direct conversion...")
                    # Ne pas lever d'erreur, essayer directement la conversion
                else:
                    error_msg = f"""
                                        VIPS is not found or not accessible. 

                                        Please install libvips-tools:
                                        - Windows: Download from https://github.com/libvips/libvips/releases or use choco: choco install vips
                                        - Ubuntu/Debian: sudo apt-get install libvips-tools  
                                        - macOS: brew install vips

                                        Make sure vips is in your PATH and restart the backend server.
                    """
                    print(error_msg)
                    raise HTTPException(status_code=500, detail=error_msg.strip())

            print("Step 1: Creating temp directory...")
            with tempfile.TemporaryDirectory() as tmp:
                in_path = os.path.join(tmp, "input_wsi")
                out_dir = os.path.join(tmp, "slide")
                print(f"Temp directory: {tmp}")

                # 1) Télécharger la WSI depuis MinIO (async wrapper)
                print("Step 2: Downloading WSI from MinIO...")
                def download_file():
                    try:
                        print(f"Downloading object: {object_name}")
                        data = minio.get_object_bytes(object_name)
                        if data is None:
                            print("Object not found or download failed")
                            return None
                        print(f"Downloaded {len(data)} bytes")
                        return data
                    except Exception as e:
                        print(f"Download error: {str(e)}")
                        raise e
                
                data = await asyncio.get_event_loop().run_in_executor(None, download_file)
                if data is None:
                    raise HTTPException(status_code=404, detail="WSI object not found in MinIO")

                print("Step 3: Writing WSI to temp file...")
                with open(in_path, "wb") as f:
                    f.write(data)
                print(f"WSI file written: {len(data)} bytes")

                # 2) Générer DZI via vips avec options optimisées
                print("Step 4: Starting VIPS conversion...")
                cmd = [
                    vips_path, "dzsave",
                    in_path,
                    out_dir,
                    "--suffix=.jpg",
                    "--tile-size=512",  # Tiles plus grandes = moins de fichiers
                    "--overlap=0",
                    "--layout=dz",
                    "--depth=onepixel",  # Générer tous les niveaux jusqu'au pixel
                    "--compression=8",  # Compression JPEG équilibrée
                ]
                
                try:
                    print(f"Starting vips conversion: {' '.join(cmd)}")
                    
                    # Utiliser subprocess.run dans un executor pour compatibilité Windows
                    def run_vips():
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=1800  # 30 minutes timeout
                        )
                        return result
                    
                    result = await asyncio.get_event_loop().run_in_executor(None, run_vips)
                    
                    print(f"VIPS return code: {result.returncode}")
                    if result.stdout:
                        print(f"VIPS stdout: {result.stdout}")
                    if result.stderr:
                        print(f"VIPS stderr: {result.stderr}")
                    
                    if result.returncode != 0:
                        error_msg = result.stderr if result.stderr else f"VIPS failed with code {result.returncode}"
                        print(f"VIPS error: {error_msg}")
                        raise HTTPException(status_code=500, detail=f"vips dzsave failed: {error_msg}")
                        
                except Exception as e:
                    print(f"Exception during vips execution: {str(e)}")
                    # Vérifier si vips est installé
                    try:
                        import subprocess
                        result = subprocess.run(["vips", "--version"], capture_output=True, text=True)
                        print(f"VIPS version: {result.stdout}")
                    except FileNotFoundError:
                        print("VIPS is not installed or not in PATH")
                        raise HTTPException(status_code=500, detail="VIPS is not installed. Please install libvips-tools.")
                    
                    raise HTTPException(status_code=500, detail=f"vips dzsave failed: {str(e)}")

                print("Step 5: Checking generated files...")
                # 3) Uploader .dzi + tiles dans MinIO en parallèle
                dzi_path = out_dir + ".dzi"
                files_dir = out_dir + "_files"

                print(f"Checking DZI file: {dzi_path}")
                print(f"DZI file exists: {os.path.exists(dzi_path)}")
                
                print(f"Checking tiles directory: {files_dir}")
                print(f"Tiles directory exists: {os.path.exists(files_dir)}")

                if not os.path.exists(dzi_path):
                    raise HTTPException(status_code=500, detail="DZI file not generated")

                if not os.path.exists(files_dir):
                    print("ERROR: Tiles directory was not created by VIPS!")
                    print("Listing temp directory contents:")
                    for item in os.listdir(tmp):
                        item_path = os.path.join(tmp, item)
                        if os.path.isdir(item_path):
                            print(f"  DIR: {item}/")
                            for subitem in os.listdir(item_path):
                                print(f"    {subitem}")
                        else:
                            print(f"  FILE: {item}")
                    raise HTTPException(status_code=500, detail="Tiles directory not generated by VIPS")

                print(f"DZI file generated: {dzi_path}")
                print(f"Tiles directory: {files_dir}")

                # Upload du fichier DZI
                print("Step 6: Uploading DZI file...")
                dzi_object = f"patients/{patient_id}/dzi/{wsi_id}/slide.dzi"
                
                def upload_dzi():
                    try:
                        with open(dzi_path, "rb") as f:
                            content = f.read()
                            print(f"Uploading DZI: {len(content)} bytes")
                            minio.upload_file(content, dzi_object, "application/xml")
                            print("DZI upload completed successfully")
                    except Exception as e:
                        print(f"Upload DZI error: {str(e)}")
                        raise e
                
                await asyncio.get_event_loop().run_in_executor(None, upload_dzi)

                # Collecter tous les fichiers tiles
                print("Step 7: Collecting tile files...")
                tile_files = []
                if os.path.exists(files_dir):
                    for root, _, filenames in os.walk(files_dir):
                        for name in filenames:
                            local_path = os.path.join(root, name)
                            rel = os.path.relpath(local_path, files_dir)
                            tile_files.append((local_path, rel))
                            print(f"Found tile: {rel}")
                
                print(f"Found {len(tile_files)} tile files")

                if not tile_files:
                    print("ERROR: No tile files found in tiles directory!")
                    print("Directory structure:")
                    for root, dirs, files in os.walk(files_dir):
                        level = root.replace(files_dir, '').count(os.sep)
                        indent = ' ' * 2 * level
                        print(f"{indent}{os.path.basename(root)}/")
                        subindent = ' ' * 2 * (level + 1)
                        for file in files:
                            print(f"{subindent}{file}")
                    return

                # Upload des tiles par lots de 50 pour optimiser
                print("Step 8: Uploading tiles...")
                batch_size = 50
                total_batches = (len(tile_files) - 1) // batch_size + 1
                
                for i in range(0, len(tile_files), batch_size):
                    batch = tile_files[i:i + batch_size]
                    print(f"Uploading batch {i//batch_size + 1}/{total_batches} ({len(batch)} tiles)")
                    
                    # Afficher quelques tiles de ce batch pour debug
                    if i == 0:  # Premier batch
                        print(f"Sample tiles in first batch: {[rel for _, rel in batch[:5]]}")
                    elif i == len(tile_files) - len(tile_files) % batch_size:  # Dernier batch
                        print(f"Sample tiles in last batch: {[rel for _, rel in batch[-5:]]}")
                    
                    try:
                        await asyncio.wait_for(
                            _upload_tile_batch(batch, patient_id, wsi_id),
                            timeout=300  # 5 minutes par batch
                        )
                        print(f"Batch {i//batch_size + 1} uploaded successfully")
                    except asyncio.TimeoutError:
                        print(f"ERROR: Batch {i//batch_size + 1} upload timeout after 5 minutes")
                        print(f"Last tile in batch: {batch[-1][1] if batch else 'None'}")
                        raise HTTPException(status_code=500, detail=f"Upload timeout on batch {i//batch_size + 1}")
                    except Exception as e:
                        print(f"ERROR uploading batch {i//batch_size + 1}: {str(e)}")
                        print(f"Last tile in batch: {batch[-1][1] if batch else 'None'}")
                        raise e

                print("=== DZI Conversion Completed Successfully ===")
                print(f"Total tiles uploaded: {len(tile_files)}")
                print(f"Total batches processed: {total_batches}")

        except Exception as e:
            print(f"=== DZI Conversion Failed ===")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Ne pas lever d'exception ici pour éviter de casser le background task
            # Mais on pourrait logger l'erreur dans un système de monitoring

    # Ajouter la tâche en arrière-plan pour retourner immédiatement
    background_tasks.add_task(_convert_and_upload)
    
    return {
        "message": "DZI conversion started", 
        "wsi_id": wsi_id,
        "patient_id": patient_id,
        "object_name": object_name,
        "status": "processing"
    }

@router.get("/patients/{patient_id}/{wsi_id}/dzi")
def get_dzi(patient_id: str, wsi_id: str):
    obj = f"patients/{patient_id}/dzi/{wsi_id}/slide.dzi"
    data = minio.get_object_bytes(obj)
    if data is None:
        raise HTTPException(status_code=404, detail=f"DZI not found: {obj}")
    return Response(content=data, media_type="application/xml")

@router.get("/patients/{patient_id}/{wsi_id}/slide_files/{path:path}")
def get_tile(patient_id: str, wsi_id: str, path: str):
    obj = f"patients/{patient_id}/dzi/{wsi_id}/slide_files/{path}"
    data = minio.get_object_bytes(obj)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Tile not found: {obj}")
    return Response(content=data, media_type="image/jpeg")

@router.get("/openseadragon-images/{file_name}")
def get_openseadragon_image(file_name: str):
    """Servir les images OpenSeadragon (logos, etc.)"""
    # Chemin vers le dossier node_modules/openseadragon/build/openseadragon/images
    frontend_path = Path(__file__).parent.parent.parent.parent.parent / "frontend" / "node_modules" / "openseadragon" / "build" / "openseadragon" / "images"
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
    return Response(content=data, media_type="image/jpeg")