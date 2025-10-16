# MinIO Python FastAPI File Storage

A single-file FastAPI application that implements complete CRUD (Create, Read, Update, Delete) operations for file management using MinIO for object storage and SQLite for metadata persistence.

## Features

- **Upload Files**: Upload files to MinIO storage with automatic metadata tracking
- **List Files**: Retrieve all file metadata from SQLite database
- **Download Files**: Download files from MinIO by file ID
- **Delete Files**: Remove files from both MinIO and SQLite
- **Single File Application**: All functionality in one runnable Python file
- **RESTful API**: Clean FastAPI endpoints with automatic documentation

## Tech Stack

- **FastAPI**: Modern Python web framework for building APIs
- **MinIO**: High-performance object storage (S3-compatible)
- **SQLite**: Lightweight database for file metadata
- **Uvicorn**: ASGI server for running the application

## Prerequisites

- Python 3.8+
- Docker and Docker Compose (for running MinIO)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Ruzimurod2003/minio-python-app.git
cd minio-python-app
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Start MinIO using Docker Compose:
```bash
docker-compose up -d
```

This will start MinIO on:
- API: http://localhost:9000
- Console: http://localhost:9001 (login with minioadmin/minioadmin)

## Configuration

The application can be configured using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO server endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `files` | MinIO bucket name |
| `MINIO_SECURE` | `false` | Use HTTPS for MinIO connection |
| `DATABASE_PATH` | `files.db` | SQLite database file path |

## Usage

### Start the Application

```bash
python app.py
```

Or with uvicorn directly:
```bash
uvicorn app:app --reload
```

The API will be available at http://localhost:8000

### API Documentation

Interactive API documentation is automatically available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### API Endpoints

#### 1. Upload File
```bash
curl -X POST "http://localhost:8000/files/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/file.txt"
```

Response:
```json
{
  "id": 1,
  "filename": "file.txt",
  "minio_object_key": "uuid_file.txt",
  "message": "File uploaded successfully"
}
```

#### 2. List All Files
```bash
curl -X GET "http://localhost:8000/files/"
```

Response:
```json
[
  {
    "id": 1,
    "filename": "file.txt",
    "minio_object_key": "uuid_file.txt",
    "content_type": "text/plain",
    "size": 1024,
    "created_at": "2024-01-01 12:00:00"
  }
]
```

#### 3. Download File
```bash
curl -X GET "http://localhost:8000/files/1" --output downloaded_file.txt
```

#### 4. Delete File
```bash
curl -X DELETE "http://localhost:8000/files/1"
```

Response:
```json
{
  "message": "File 1 deleted successfully"
}
```

## File Structure

```
minio-python-app/
├── app.py                 # Main FastAPI application (single file)
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # MinIO setup
├── README.md             # This file
└── files.db              # SQLite database (auto-created)
```

## Database Schema

The SQLite database contains a single `files` table:

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    minio_object_key TEXT NOT NULL UNIQUE,
    content_type TEXT,
    size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Architecture

1. **File Upload Flow**:
   - Client sends file via multipart/form-data
   - Application generates unique object key (UUID + filename)
   - File is uploaded to MinIO bucket
   - Metadata is stored in SQLite database
   - Returns file ID and metadata

2. **File Download Flow**:
   - Client requests file by ID
   - Application queries SQLite for object key
   - File is retrieved from MinIO
   - File is streamed to client

3. **File Delete Flow**:
   - Client requests deletion by ID
   - Application queries SQLite for object key
   - File is removed from MinIO
   - Metadata is deleted from SQLite

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest httpx

# Run tests (when available)
pytest
```

### Code Style

The application follows Python best practices:
- Type hints for better code clarity
- Pydantic models for request/response validation
- Proper error handling with HTTP exceptions
- Environment-based configuration

## Troubleshooting

### MinIO Connection Issues

1. Ensure MinIO is running:
   ```bash
   docker-compose ps
   ```

2. Check MinIO logs:
   ```bash
   docker-compose logs minio
   ```

3. Verify MinIO is accessible:
   ```bash
   curl http://localhost:9000/minio/health/live
   ```

### Database Issues

If you encounter database errors, try removing the database file:
```bash
rm files.db
```

The application will recreate it on next startup.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.