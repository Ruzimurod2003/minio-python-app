#!/usr/bin/env python3
"""
Example script demonstrating how to use the File Storage API.
"""
import requests

# API base URL
BASE_URL = "http://localhost:8000"


def upload_file(file_path: str):
    """Upload a file to the API."""
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/files/", files=files)
        response.raise_for_status()
        return response.json()


def list_files():
    """List all files."""
    response = requests.get(f"{BASE_URL}/files/")
    response.raise_for_status()
    return response.json()


def download_file(file_id: int, output_path: str):
    """Download a file by ID."""
    response = requests.get(f"{BASE_URL}/files/{file_id}")
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        f.write(response.content)
    print(f"File downloaded to {output_path}")


def delete_file(file_id: int):
    """Delete a file by ID."""
    response = requests.delete(f"{BASE_URL}/files/{file_id}")
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # Example usage
    print("=== File Storage API Example ===\n")
    
    # Upload a file
    print("1. Uploading file...")
    result = upload_file("/tmp/test_file.txt")
    print(f"   Uploaded: {result}")
    file_id = result['id']
    
    # List all files
    print("\n2. Listing all files...")
    files = list_files()
    for file in files:
        print(f"   - {file['filename']} (ID: {file['id']}, Size: {file['size']} bytes)")
    
    # Download a file
    print(f"\n3. Downloading file ID {file_id}...")
    download_file(file_id, "/tmp/downloaded.txt")
    
    # Delete a file
    print(f"\n4. Deleting file ID {file_id}...")
    result = delete_file(file_id)
    print(f"   {result['message']}")
    
    # List files again
    print("\n5. Listing files after deletion...")
    files = list_files()
    if files:
        for file in files:
            print(f"   - {file['filename']} (ID: {file['id']})")
    else:
        print("   No files found")
