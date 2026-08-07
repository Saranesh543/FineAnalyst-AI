from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.chat import FileAttachment
from app.services.file_service import file_service
router = APIRouter(prefix="/files", tags=["Files"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

ALLOWED_EXTENSIONS = {
    ".csv", ".xlsx", ".xls", ".json", ".db", ".sqlite",
    ".pdf", ".doc", ".docx", ".txt",
    ".png", ".jpg", ".jpeg"
}

@router.post("/upload")
async def upload_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("[File Upload] Received upload request: user_id=%s, session_id=%s, filename=%s, content_type=%s", 
                current_user.id, session_id, file.filename, file.content_type)
                
    ext = os.path.splitext(file.filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning("[File Upload] Rejected unsupported file type: %s", ext)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}"
        )
        
    try:
        logger.info("[File Upload] Processing upload for %s...", file.filename)
        attachment = await file_service.process_upload(
            file=file,
            session_id=session_id,
            user_id=current_user.id,
            db=db
        )
        logger.info("[File Upload] Successfully processed %s. DB ID: %s, table: %s", 
                    file.filename, attachment.id, attachment.table_name)
        return {
            "id": attachment.id,
            "filename": attachment.filename,
            "size_bytes": attachment.size_bytes,
            "file_type": attachment.file_type
        }
    except Exception as e:
        logger.exception("[File Upload] Failed to process file %s: %s", file.filename, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )

@router.get("/session/{session_id}")
async def get_session_files(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileAttachment).where(
            FileAttachment.session_id == session_id,
            FileAttachment.user_id == current_user.id
        )
    )
    files = result.scalars().all()
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "size_bytes": f.size_bytes,
            "file_type": f.file_type,
            "table_name": f.table_name
        }
        for f in files
    ]

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileAttachment).where(
            FileAttachment.id == file_id,
            FileAttachment.user_id == current_user.id
        )
    )
    attachment = result.scalars().first()
    
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
        
    # delete from db
    await db.delete(attachment)
    await db.commit()
    
    # optionally delete table from user's analytics DB if it was a structured file
    if attachment.table_name:
        try:
            from sqlalchemy import create_engine, text
            user_db_path = f"./analytics_user_{current_user.id}.db"
            engine = create_engine(f"sqlite:///{user_db_path}")
            with engine.begin() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {attachment.table_name}"))
        except Exception:
            pass # ignore errors here
            
    return {"message": "File deleted successfully"}
