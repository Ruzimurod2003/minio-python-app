"""
FastAPI application for file CRUD operations with MinIO storage and SQLite metadata.
"""
import io
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel
import urllib3

from dotenv import load_dotenv
load_dotenv()

# Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "files")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
DATABASE_PATH = os.getenv("DATABASE_PATH", "files.db")

http_client = None
if os.getenv("MINIO_INSECURE_TLS") == "1":
    http_client = urllib3.PoolManager(cert_reqs="CERT_NONE")

# MinIO client
minio_client = Minio(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
    http_client=http_client
)


# Database setup
def init_db():
    """Initialize SQLite database with file metadata table."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            minio_object_key TEXT NOT NULL UNIQUE,
            content_type TEXT,
            size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def ensure_bucket():
    """Ensure MinIO bucket exists."""
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            print(f"Bucket '{MINIO_BUCKET}' created successfully")
        else:
            print(f"Bucket '{MINIO_BUCKET}' already exists")
    except S3Error as e:
        print(f"Error ensuring bucket: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    init_db()
    ensure_bucket()
    yield
    # Shutdown (cleanup if needed)


# FastAPI app
app = FastAPI(
    title="File Storage API",
    description="FastAPI application with MinIO storage and SQLite metadata",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models
class FileMetadata(BaseModel):
    id: int
    filename: str
    minio_object_key: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    created_at: str


class FileUploadResponse(BaseModel):
    id: int
    filename: str
    minio_object_key: str
    message: str


# Helper functions
def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "File Storage API with MinIO and SQLite",
        "endpoints": {
            "POST /files/": "Upload a file",
            "GET /files/": "List all files",
            "GET /files/{file_id}": "Download a file",
            "DELETE /files/{file_id}": "Delete a file"
        }
    }


@app.post("/files/", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to MinIO and store metadata in SQLite.
    
    Args:
        file: The file to upload
    
    Returns:
        FileUploadResponse with file metadata
    """
    try:
        # Generate unique object key
        object_key = f"{uuid.uuid4()}_{file.filename}"
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Upload to MinIO
        minio_client.put_object(
            MINIO_BUCKET,
            object_key,
            io.BytesIO(file_content),
            length=file_size,
            content_type=file.content_type or "application/octet-stream"
        )
        
        # Store metadata in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO files (filename, minio_object_key, content_type, size)
            VALUES (?, ?, ?, ?)
            """,
            (file.filename, object_key, file.content_type, file_size)
        )
        conn.commit()
        file_id = cursor.lastrowid
        conn.close()
        
        return FileUploadResponse(
            id=file_id,
            filename=file.filename,
            minio_object_key=object_key,
            message="File uploaded successfully"
        )
        
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


@app.get("/files/", response_model=List[FileMetadata])
async def list_files():
    """
    List all files with metadata from SQLite.
    
    Returns:
        List of FileMetadata objects
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, filename, minio_object_key, content_type, size, created_at FROM files ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        
        files = [
            FileMetadata(
                id=row["id"],
                filename=row["filename"],
                minio_object_key=row["minio_object_key"],
                content_type=row["content_type"],
                size=row["size"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
        
        return files
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@app.get("/files/{file_id}")
async def download_file(file_id: int):
    """
    Download a file from MinIO by file ID.
    
    Args:
        file_id: The database ID of the file
    
    Returns:
        StreamingResponse with file content
    """
    try:
        # Get file metadata from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT filename, minio_object_key, content_type FROM files WHERE id = ?",
            (file_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="File not found")
        
        filename = row["filename"]
        object_key = row["minio_object_key"]
        content_type = row["content_type"] or "application/octet-stream"
        
        # Get file from MinIO
        response = minio_client.get_object(MINIO_BUCKET, object_key)
        
        # Stream the file
        return StreamingResponse(
            response.stream(32 * 1024),  # 32KB chunks
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")


@app.delete("/files/{file_id}")
async def delete_file(file_id: int):
    """
    Delete a file from both MinIO and SQLite.
    
    Args:
        file_id: The database ID of the file to delete
    
    Returns:
        Success message
    """
    try:
        # Get file metadata from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT minio_object_key FROM files WHERE id = ?",
            (file_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="File not found")
        
        object_key = row["minio_object_key"]
        
        # Delete from MinIO
        minio_client.remove_object(MINIO_BUCKET, object_key)
        
        # Delete from database
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()
        
        return {"message": f"File {file_id} deleted successfully"}
        
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
