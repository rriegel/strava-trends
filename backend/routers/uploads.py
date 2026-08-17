from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import os

from database import get_db
from services.file_upload_service import FileUploadService
from routers.auth import get_current_user
from models.user import User

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_activity_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a single activity file (FIT, GPX, or TCX).
    
    The file will be parsed and the activity will be added to the user's history.
    Duplicate detection prevents the same activity from being imported twice.
    """
    # Validate file size (max 50MB)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 50MB."
        )
    
    filename = file.filename or "unknown"
    
    # Validate file extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in FileUploadService.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: {ext}. Supported formats: {', '.join(FileUploadService.SUPPORTED_FORMATS)}"
        )
    
    try:
        service = FileUploadService(db)
        result = await service.process_upload(
            user_id=current_user.id,
            file_content=content,
            filename=filename
        )
        
        if result["status"] == "duplicate":
            return {
                "status": "duplicate",
                "message": "This activity was already imported",
                "activity_id": result.get("activity_id")
            }
        
        return {
            "status": "success",
            "message": "Activity imported successfully",
            "activity_id": result.get("activity_id"),
            "activity_name": result.get("activity_name"),
            "activity_type": result.get("activity_type"),
            "start_date": result.get("start_date")
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing dependency: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )

@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload multiple activity files at once.
    
    Each file is processed independently. Returns results for all files.
    """
    results = []
    
    for file in files:
        content = await file.read()
        filename = file.filename or "unknown"
        
        # Skip files that are too large
        if len(content) > 50 * 1024 * 1024:
            results.append({
                "filename": filename,
                "status": "error",
                "message": "File too large (max 50MB)"
            })
            continue
        
        # Skip unsupported formats
        ext = os.path.splitext(filename)[1].lower()
        if ext not in FileUploadService.SUPPORTED_FORMATS:
            results.append({
                "filename": filename,
                "status": "error",
                "message": f"Unsupported format: {ext}"
            })
            continue
        
        try:
            service = FileUploadService(db)
            result = await service.process_upload(
                user_id=current_user.id,
                file_content=content,
                filename=filename
            )
            
            results.append({
                "filename": filename,
                **result
            })
        
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e)
            })
    
    # Summary
    success_count = sum(1 for r in results if r.get("status") == "success")
    duplicate_count = sum(1 for r in results if r.get("status") == "duplicate")
    error_count = sum(1 for r in results if r.get("status") == "error")
    
    return {
        "total_files": len(files),
        "success_count": success_count,
        "duplicate_count": duplicate_count,
        "error_count": error_count,
        "results": results
    }

@router.get("/supported-formats")
async def get_supported_formats():
    """
    Get list of supported file formats for upload.
    """
    return {
        "formats": list(FileUploadService.SUPPORTED_FORMATS),
        "max_file_size_mb": 50,
        "description": {
            ".fit": "Garmin FIT files (binary format, most common from Garmin devices)",
            ".gpx": "GPX files (GPS exchange format, widely supported)",
            ".tcx": "TCX files (Training Center XML, older Garmin format)"
        }
    }
