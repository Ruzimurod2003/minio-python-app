#!/bin/bash
# Integration test script for the File Storage API

set -e

echo "=== File Storage API Integration Test ==="
echo ""

# Check if MinIO is running
echo "1. Checking MinIO availability..."
if ! curl -f -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "   MinIO is not running. Please start it with: docker compose up -d"
    exit 1
fi
echo "   ✓ MinIO is running"

# Check if API is running
echo ""
echo "2. Checking API availability..."
if ! curl -f -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "   API is not running. Please start it with: python app.py"
    exit 1
fi
echo "   ✓ API is running"

# Create test files
echo ""
echo "3. Creating test files..."
echo "Test content for text file" > /tmp/test_text.txt
dd if=/dev/urandom of=/tmp/test_binary.bin bs=1024 count=5 2>/dev/null
echo "   ✓ Test files created"

# Test file upload
echo ""
echo "4. Testing file upload (text file)..."
RESPONSE=$(curl -s -X POST http://localhost:8000/files/ -F "file=@/tmp/test_text.txt")
FILE_ID_1=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "   ✓ Text file uploaded with ID: $FILE_ID_1"

echo ""
echo "5. Testing file upload (binary file)..."
RESPONSE=$(curl -s -X POST http://localhost:8000/files/ -F "file=@/tmp/test_binary.bin")
FILE_ID_2=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "   ✓ Binary file uploaded with ID: $FILE_ID_2"

# Test list files
echo ""
echo "6. Testing list files..."
FILES=$(curl -s http://localhost:8000/files/)
FILE_COUNT=$(echo $FILES | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "   ✓ Found $FILE_COUNT files"

# Test download
echo ""
echo "7. Testing file download..."
curl -s http://localhost:8000/files/$FILE_ID_1 -o /tmp/downloaded_test.txt
if diff -q /tmp/test_text.txt /tmp/downloaded_test.txt > /dev/null; then
    echo "   ✓ Downloaded file matches original"
else
    echo "   ✗ Downloaded file does not match original"
    exit 1
fi

# Test delete
echo ""
echo "8. Testing file delete..."
RESPONSE=$(curl -s -X DELETE http://localhost:8000/files/$FILE_ID_1)
echo "   ✓ File deleted: $(echo $RESPONSE | python3 -c 'import sys, json; print(json.load(sys.stdin)["message"])')"

# Verify deletion
echo ""
echo "9. Verifying file deletion..."
FILES=$(curl -s http://localhost:8000/files/)
FILE_COUNT=$(echo $FILES | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "   ✓ Remaining files: $FILE_COUNT"

# Test error handling (try to download deleted file)
echo ""
echo "10. Testing error handling..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/files/$FILE_ID_1)
if [ "$HTTP_CODE" == "404" ]; then
    echo "   ✓ Correctly returns 404 for deleted file"
else
    echo "   ✗ Expected 404, got $HTTP_CODE"
    exit 1
fi

# Cleanup
echo ""
echo "11. Cleaning up test data..."
curl -s -X DELETE http://localhost:8000/files/$FILE_ID_2 > /dev/null
rm -f /tmp/test_text.txt /tmp/test_binary.bin /tmp/downloaded_test.txt
echo "   ✓ Test data cleaned up"

echo ""
echo "=== All tests passed! ==="
