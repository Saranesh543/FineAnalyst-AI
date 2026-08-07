import os
import io
import uuid
import logging
from datetime import datetime, timezone
import aiofiles
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import pytesseract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from fastapi import UploadFile

from app.models.chat import FileAttachment
from app.config.settings import settings

logger = logging.getLogger(__name__)

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class FileService:
    async def process_upload(
        self, file: UploadFile, session_id: str, user_id: int, db: AsyncSession
    ) -> FileAttachment:
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1].lower()
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
        
        # Save file
        size_bytes = 0
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):
                size_bytes += len(content)
                await out_file.write(content)
                
        # Parse file based on extension
        extracted_text = None
        table_name = None
        
        try:
            if ext in ['.csv', '.xlsx', '.xls', '.json']:
                table_name = f"user_{user_id}_{file_id.replace('-', '_')}"
                await self._process_structured(file_path, ext, table_name, user_id)
            elif ext == '.sqlite' or ext == '.db':
                await self._process_sqlite(file_path, user_id, file_id)
            elif ext == '.pdf':
                extracted_text = self._extract_pdf(file_path)
            elif ext in ['.docx', '.doc']:
                extracted_text = self._extract_docx(file_path)
            elif ext == '.txt':
                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    extracted_text = await f.read()
            elif ext in ['.png', '.jpg', '.jpeg']:
                extracted_text = self._extract_image(file_path)
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            raise e

        # Save to DB
        attachment = FileAttachment(
            id=file_id,
            session_id=session_id,
            user_id=user_id,
            filename=file.filename,
            file_type=ext,
            size_bytes=size_bytes,
            extracted_text=extracted_text,
            table_name=table_name,
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment

    async def _process_structured(self, file_path: str, ext: str, table_name: str, user_id: int):
        user_db_path = f"./analytics_user_{user_id}.db"
        engine = create_engine(f"sqlite:///{user_db_path}")
        
        if ext == '.csv':
            df = pd.read_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif ext == '.json':
            df = pd.read_json(file_path)
        else:
            return
            
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^a-zA-Z0-9_]', '', regex=True)
        
        with engine.begin() as conn:
            df.to_sql(table_name, conn, if_exists='replace', index=False)

    async def _process_sqlite(self, file_path: str, user_id: int, file_id: str):
        source_engine = create_engine(f"sqlite:///{file_path}")
        user_db_path = f"./analytics_user_{user_id}.db"
        dest_engine = create_engine(f"sqlite:///{user_db_path}")
        
        with source_engine.connect() as src_conn:
            tables = src_conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            for (t_name,) in tables:
                df = pd.read_sql_table(t_name, src_conn)
                prefix_table_name = f"{t_name}_{file_id[:8]}"
                with dest_engine.begin() as dest_conn:
                    df.to_sql(prefix_table_name, dest_conn, if_exists='replace', index=False)

    def _extract_pdf(self, file_path: str) -> str:
        text_content = ""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Failed to read PDF: {e}")
        return text_content[:50000]

    def _extract_docx(self, file_path: str) -> str:
        text_content = ""
        try:
            doc = Document(file_path)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        except Exception as e:
            logger.error(f"Failed to read DOCX: {e}")
        return text_content[:50000]

    def _extract_image(self, file_path: str) -> str:
        text_content = ""
        try:
            img = Image.open(file_path)
            text_content = pytesseract.image_to_string(img)
        except Exception as e:
            logger.error(f"Failed to extract text from image: {e}")
        return text_content[:20000]

file_service = FileService()
