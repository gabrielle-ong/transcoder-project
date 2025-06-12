# TESTS
The following shows:
1. How to run End-to-End tests (test_upload.py)
    - video upload
    - attempt download before completion (404 Not Found, PENDING status)
    - poll status while status = `pending`, `processing` until `completion`
    - download processed file
    - download original file
    - verify processing succesful - check the 2 downloaded file codecs and the orignal local file codec with ffprobe

2. How to inspect DB for Files, Transactions

# Run End-to-End tests (test_upload.py)
There are 4 test files in `/test_files` for your easy testing
- test_files/sintel_265_2s.mp4 (format: hevc, size: 430KB)
- test_files/bunny_264_2s.mp4 (format: h.264, size: 1.5MB)
- test_files/sintel_265_large.mp4 (format: hevc, size: 3.4MB)
- test_files/bunny_264_large.mp4 (format: h.264, size: 7.2MB)

## How to run
### 1. In a first terminal, run docker compose. Wait for db, api and worker containers to run successfully
```bash
❯ docker-compose up --build
```

### 2. In a separate terminal, run test_upload.py
```bash
❯ python3 test_upload.py
```

------
## Sample test results:
```bash
❯ python3 test_upload.py

================================================================================
STARTING E2E TEST FOR: test_files/bunny_264_2s.mp4
================================================================================

--- Step 1: Uploading 'bunny_264_2s.mp4' to API ---
✅ Upload successful for bunny_264_2s.mp4, File ID: 4dede76a-2304-4c10-8fdc-acd5ffb54955

--- Step 2: Unhappy Path Test: Attempting download before completion ---
response: <Response [404]>
✅ Received expected 404 Not Found.
✅ Response contains correct error message: 'Processed file not available. Current File status: ProcessingStatus.PENDING'

--- Step 3: Polling for processing status ---
View Docker Worker logs for video processing detailed logs. Current status: 'pending'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'processing'
View Docker Worker logs for video processing detailed logs. Current status: 'completed'
✅ Transcoding completed for bunny_264_2s.mp4! Final Status: completed

--- Step 4: Downloading and Verifying Files ---
✅ File of size 1476945 bytes downloaded successfully from S3 to test_files/original-bunny_264_2s.mp4
✅ File of size 348814 bytes downloaded successfully from S3 to test_files/processed-bunny_264_2s.mp4
Running ffprobe command: ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of compact=p=0:nk=1 -i test_files/bunny_264_2s.mp4
Running ffprobe command: ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of compact=p=0:nk=1 -i test_files/original-bunny_264_2s.mp4
Running ffprobe command: ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of compact=p=0:nk=1 -i test_files/processed-bunny_264_2s.mp4
Local test file codec: Expected 'h264', Detected 'h264'
Downloaded original file codec: Expected 'h264', Detected 'h264'
Downloaded processed file codec: Expected 'hevc', Detected 'hevc'

================================================================================
e2e tests passed for test_files/bunny_264_2s.mp4!
================================================================================

================================================================================
STARTING E2E TEST FOR: test_files/sintel_265_2s.mp4
================================================================================

--- Step 1: Uploading 'sintel_265_2s.mp4' to API ---
✅ Upload successful for sintel_265_2s.mp4, File ID: 0bae0597-1a61-417c-a373-9977c577a8ad

--- Step 2: Unhappy Path Test: Attempting download before completion ---
response: <Response [404]>
✅ Received expected 404 Not Found.
✅ Response contains correct error message: 'Processed file not available. Current File status: ProcessingStatus.PENDING'

--- Step 3: Polling for processing status ---
View Docker Worker logs for video processing detailed logs. Current status: 'pending'
View Docker Worker logs for video processing detailed logs. Current status: 'completed'
✅ Transcoding completed for sintel_265_2s.mp4! Final Status: completed

--- Step 4: Downloading and Verifying Files ---
✅ File of size 429753 bytes downloaded successfully from S3 to test_files/original-sintel_265_2s.mp4
✅ File of size 518359 bytes downloaded successfully from S3 to test_files/processed-sintel_265_2s.mp4
Running ffprobe command: ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of compact=p=0:nk=1 -i test_files/sintel_265_2s.mp4
Running ffprobe command: ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of compact=p=0:nk=1 -i test_files/original-sintel_265_2s.mp4
Running ffprobe command: ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of compact=p=0:nk=1 -i test_files/processed-sintel_265_2s.mp4
Local test file codec: Expected 'hevc', Detected 'hevc'
Downloaded original file codec: Expected 'hevc', Detected 'hevc'
Downloaded processed file codec: Expected 'h264', Detected 'h264'

================================================================================
e2e tests passed for test_files/sintel_265_2s.mp4!
================================================================================
```

# 2. Inspect Database for Files and Transactions
Connect to the database either with Docker Desktop, or terminal shell
```bash
docker ps #get container id
docker exec -it <your_db_container_id> psql -U user -d transcodedb
```

In the psql CLI,
1. List all Tables
    ```sql
    \dt
    ```
    Sample result:
    ```
                List of relations
      Schema |     Name     | Type  | Owner
     --------+--------------+-------+-------
      public | files        | table | user
      public | transactions | table | user
     (2 rows)
    ```
2. Inspect Files table
    ```sql
    select * from files;
    ```

    Sample Result:
    ```
    file_id                               |      file_name       | processing_status | original_codec | target_codec | processing_time
    --------------------------------------------------------------------+----------------------+-------------------+----------------+--------------+------------------
    a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6 | bunny_264_2s.mp4      | completed         | h264           | hevc         | 45.731
    e7f8a9b0-c1d2-e3f4-a5b6-c7d8e9f0a1b2 | sintel_265_2s.mov     | processing        | h264           |              |
    12345678-90ab-cdef-1234-567890abcdef | failed_upload.mp4     | failed            |                |              |
    (3 rows)
    ```

3. Inspect Transactions table
    ```sql
    select * from transactions;
    ```
    Sample Results:
    ```
    file_id                               |   type     |           timestamp            |                          details
    --------------------------------------------------------------------+------------+--------------------------------+-------------------------------------------------------------
    a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6 | UPLOAD     | 2025-06-12 12:30:05.123456 | Presigned URL created for upload
    a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6 | PENDING    | 2025-06-12 12:31:10.654321 | File upload complete, awaiting transcoding
    e7f8a9b0-c1d2-e3f4-a5b6-c7d8e9f0a1b2 | UPLOAD     | 2025-06-12 12:32:00.789012 | Presigned URL created for upload
    a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6 | PROCESSING | 2025-06-12 12:32:15.987654 | Starting processing
    12345678-90ab-cdef-1234-567890abcdef | UPLOAD     | 2025-06-12 12:33:00.112233 | Presigned URL created for upload
    12345678-90ab-cdef-1234-567890abcdef | FAILURE    | 2025-06-12 12:33:05.445566 | S3 upload failed: An error occurred (AccessDenied)
    e7f8a9b0-c1d2-e3f4-a5b6-c7d8e9f0a1b2 | PENDING    | 2025-06-12 12:34:20.778899 | File upload complete, awaiting transcoding
    e7f8a9b0-c1d2-e3f4-a5b6-c7d8e9f0a1b2 | PROCESSING | 2025-06-12 12:35:30.101112 | Starting processing
    a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6 | COMPLETION | 2025-06-12 12:36:15.876543 | Completed in 45.73s
    ```