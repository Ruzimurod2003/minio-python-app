import io
import uuid
import urllib3
from fastapi import UploadFile
from collections.abc import Iterator
from minio import Minio, S3Error, S3Error


def get_client(MINIO_INSECURE_TLS: int, MINIO_ENDPOINT: str, MINIO_ACCESS_KEY: str, MINIO_SECRET_KEY: str, MINIO_SECURE: bool):
    http_client = None
    if MINIO_INSECURE_TLS == 1:
        http_client = urllib3.PoolManager(cert_reqs="CERT_NONE")

    minio_client = Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
        http_client=http_client
    )

    return minio_client

def ensure_bucket(
        MINIO_INSECURE_TLS: int, 
        MINIO_ENDPOINT: str, 
        MINIO_ACCESS_KEY: str, 
        MINIO_SECRET_KEY: str, 
        MINIO_SECURE: bool, 
        MINIO_BUCKET: str
    ):
    minio_client = get_client(MINIO_INSECURE_TLS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE)

    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            print(f"Bucket '{MINIO_BUCKET}' created successfully")
        else:
            print(f"Bucket '{MINIO_BUCKET}' already exists")
    except S3Error as e:
        print(f"Error ensuring bucket: {e}")
        raise

async def upload_file_to_minio(
        MINIO_INSECURE_TLS: int, 
        MINIO_ENDPOINT: str, 
        MINIO_ACCESS_KEY: str, 
        MINIO_SECRET_KEY: str, 
        MINIO_SECURE: bool, 
        MINIO_BUCKET: str, 
        file: UploadFile
    ):
    file_extension = file.filename.split(".")[-1]
    object_key = f"{uuid.uuid4()}_file.{file_extension}"
    
    file_content = await file.read()
    file_size = len(file_content)
    content_type = file.content_type or "application/octet-stream"
    minio_client = get_client(MINIO_INSECURE_TLS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE)

    minio_client.put_object(
        MINIO_BUCKET,
        object_key,
        io.BytesIO(file_content),
        length=file_size,
        content_type=content_type
    )

    return (file.filename, object_key, file_size, content_type)

def download_file_from_minio(
        MINIO_INSECURE_TLS: int, 
        MINIO_ENDPOINT: str, 
        MINIO_ACCESS_KEY: str, 
        MINIO_SECRET_KEY: str, 
        MINIO_SECURE: bool, 
        MINIO_BUCKET: str, 
        object_key: str
    ) -> Iterator[bytes]:
    minio_client = get_client(MINIO_INSECURE_TLS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE)

    response = minio_client.get_object(MINIO_BUCKET, object_key)

    return response.stream()

def delete_file_from_minio(
        MINIO_INSECURE_TLS: int, 
        MINIO_ENDPOINT: str, 
        MINIO_ACCESS_KEY: str, 
        MINIO_SECRET_KEY: str, 
        MINIO_SECURE: bool, 
        MINIO_BUCKET: str, 
        object_key: str
    ):
    minio_client = get_client(MINIO_INSECURE_TLS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE)

    minio_client.remove_object(MINIO_BUCKET, object_key)