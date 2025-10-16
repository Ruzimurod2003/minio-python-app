import sqlite3
from typing import Optional
from models.file_model import FileMetadata

def get_db_connection(DATABASE_PATH: str):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(DATABASE_PATH: str):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            minio_object_key TEXT NOT NULL UNIQUE,
            content_type TEXT,
            size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_file_metadata(
        DATABASE_PATH: str, 
        file_name: str, 
        object_key: str, 
        content_type: Optional[str], 
        file_size: Optional[int]
    ) -> FileMetadata:
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO files (file_name, minio_object_key, content_type, size)
        VALUES (?, ?, ?, ?)
        """,
        (file_name, object_key, content_type, file_size)
    )
    conn.commit()
    file_id = cursor.lastrowid
    conn.close()
    
    file = get_file_metadata(DATABASE_PATH, file_id)
    return file

def list_files(DATABASE_PATH: str) -> list[FileMetadata]:
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, file_name, minio_object_key, content_type, size, created_at FROM files ORDER BY created_at DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    
    files = [
        FileMetadata(
            id=row["id"],
            file_name=row["file_name"],
            minio_object_key=row["minio_object_key"],
            content_type=row["content_type"],
            size=row["size"],
            created_at=row["created_at"]
        )
        for row in rows
    ]
    return files
    
def get_file_metadata(DATABASE_PATH: str, file_id: int) -> Optional[FileMetadata]:
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT file_name, minio_object_key, content_type FROM files WHERE id = ?",
        (file_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return FileMetadata(
        id=file_id,
        file_name=row["file_name"],
        minio_object_key=row["minio_object_key"],
        content_type=row["content_type"]
    )    

def delete_file_metadata(DATABASE_PATH: str, file_id: int) -> bool:
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM files WHERE id = ?",
        (file_id,)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return deleted