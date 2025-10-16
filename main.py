import os
import uvicorn
from typing import List
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, File, HTTPException, UploadFile
from models.file_model import FileMetadata, FileUploadResponse
from services.database_service import add_file_metadata, delete_file_metadata, get_file_metadata, init_db, list_files
from services.minio_service import delete_file_from_minio, download_file_from_minio, ensure_bucket, upload_file_to_minio

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "files")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
DATABASE_PATH = os.getenv("DATABASE_PATH", "files.db")
MINIO_INSECURE_TLS = int(os.getenv("MINIO_INSECURE_TLS", "0"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DATABASE_PATH)
    ensure_bucket(MINIO_INSECURE_TLS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE, MINIO_BUCKET)
    yield

app = FastAPI(
    title="File Storage API",
    description="FastAPI application with MinIO storage and SQLite metadata",
    version="1.0.0",
    lifespan=lifespan
)

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
    try:
        (file_name, object_key, file_size, content_type) = await upload_file_to_minio(MINIO_INSECURE_TLS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE, MINIO_BUCKET, file)
                
        file_id = add_file_metadata(DATABASE_PATH, file_name, object_key, content_type, file_size)
        
        return FileUploadResponse(
            id=file_id,
            file_name=file_name,
            minio_object_key=object_key,
            message="File uploaded successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/", response_model=List[FileMetadata])
async def list_files_endpoint():
    try:
        files = list_files(DATABASE_PATH)
        
        return files        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}")
async def download_file(file_id: int):
    try:
        file = get_file_metadata(DATABASE_PATH, file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        res = download_file_from_minio(MINIO_INSECURE_TLS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE, MINIO_BUCKET, file.minio_object_key)
        
        return StreamingResponse(
            res,
            media_type=file.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file.file_name}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{file_id}")
async def delete_file(file_id: int):
    try:
        file = get_file_metadata(DATABASE_PATH, file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found in database")
        
        object_key = file["minio_object_key"]
        delete_file_from_minio(MINIO_INSECURE_TLS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE, MINIO_BUCKET, object_key)
                
        deleted = delete_file_metadata(DATABASE_PATH, file_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found in database")

        return {"message": f"File {file_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
