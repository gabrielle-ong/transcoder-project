
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