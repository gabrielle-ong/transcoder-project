"""
#### PRE REQUISITES ####
To run this end to end test locally, you need:
1. Two test files provided (test_filess/bunny_264_2s.mp4, test_files/sintel_265_2s.mp)
2. ffmpeg to verify the video codecs 
3. `pip install -r requirements.txt`

You can download ffmpeg via `brew install ffmpeg` (MacOS) or `sudo apt install ffmpeg` (Debian/Ubuntu)
"""

import requests
import os
import time
import subprocess
import sys

# --- Configuration ---
BASE_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{BASE_URL}/upload"
TESTS_FILES_FOLDER = "test_files"
TEST_FILES = {
    f"{TESTS_FILES_FOLDER}/sintel_265_2s.mp4": {"original": "hevc", "processed": "h264"},
    f"{TESTS_FILES_FOLDER}/bunny_264_2s.mp4": {"original": "h264", "processed": "hevc"},
}

def test_upload_file(filepath: str) -> str:
    """Tests Uploads file with a file object and returns file_id"""
    
    print(f"\n--- Step 1: Uploading '{os.path.basename(file_path)}' to API ---")

    with open(filepath, 'rb') as f:
        response = requests.post(UPLOAD_ENDPOINT, files={'file': f})
    response.raise_for_status()
    file_id = response.json()['file_id']
    if file_id:
            print(f"✅ Upload successful for {os.path.basename(file_path)}, File ID: {file_id}")
    return file_id

def test_unhappy_path_download(file_id: str):
    """Tests that downloading a file before it's ready returns a 404 error."""
    
    print("\n--- Step 2: Unhappy Path Test: Attempting download before completion ---")
    download_processed_endpoint = f"{BASE_URL}/upload/{file_id}/download/processed"
    response = requests.get(download_processed_endpoint)
    print(f"response: {response}")
    assert response.status_code == 404
    print(f"✅ Received expected 404 Not Found.")
    
    response_json = response.json()
    assert "not available" in response_json.get("detail", "")
    print(f"✅ Response contains correct error message: '{response_json.get('detail')}'")


def test_poll_for_completion(file_id: str) -> dict:
    """Polls the status endpoint, expects pending until processing is complete or failed."""
    
    print("\n--- Step 3: Polling for processing status ---")
    status_endpoint = f"{UPLOAD_ENDPOINT}/{file_id}/status"

    timeout = 300 # 5min. above smaller test files should take about 30s - 1m depending on local specs
    start_time = time.time()

    while True:
        response = requests.get(status_endpoint)
        response.raise_for_status()
        status_json = response.json()
        status = status_json.get("processing_status")
        print(f"View Docker Worker logs for video processing detailed logs. Current status: '{status}'")
        if status in ["completed", "failed"]:
            break
        if time.time() - start_time > timeout:
            print("timeout")
            break
        time.sleep(5)

    if status != "completed":
        raise RuntimeError(f"Transcoding failed with final status: '{status}'")

    print(f"✅ Transcoding completed for {os.path.basename(file_path)}! Final Status: {status}")

def download_to_local(download_endpoint: str, file_path: str, local_path: str):
    # get s3 Presigned URLS
    s3_url = requests.get(download_endpoint).json()['download_url']
    file_req = requests.get(s3_url)
    file_req.raise_for_status()
    with open(local_path, 'wb') as f:
        f.write(file_req.content)
    print(f"✅ File of size {len(file_req.content)} bytes downloaded successfully from S3 to {local_path}")

def get_local_file_codec(file_path: str) -> str:
    """ Detects codec of a local file_path, returns either h264 or hevc"""
    if not os.path.exists(file_path):
        print(f"  [TEST_ERROR] Codec check failed: File not found at {file_path}")
        return None
        
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name", "-of", "compact=p=0:nk=1",
        "-i", file_path,
    ]
    try:
        print(f"Running ffprobe command: {' '.join(command)}")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        codec_str = result.stdout.strip()
        return codec_str
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe get codec failed: {e.stderr}")
    
def test_download_and_verify_codecs(file_id: str, file_path: str, expected_codecs: dict):
    """Downloads processed files and verifies both original and processed codecs using ffprobe."""
    
    print("\n--- Step 4: Downloading and Verifying Files ---")
    download_original_endpoint = f"{BASE_URL}/upload/{file_id}/download/original"
    download_processed_endpoint = f"{BASE_URL}/upload/{file_id}/download/processed"
    original_local_path = f"{TESTS_FILES_FOLDER}/original-{os.path.basename(file_path)}"
    processed_local_path = f"{TESTS_FILES_FOLDER}/processed-{os.path.basename(file_path)}"
    
    temp_files_to_clean = []
    try:
        download_to_local(download_original_endpoint, file_path, original_local_path)
        download_to_local(download_processed_endpoint, file_path, processed_local_path)
        temp_files_to_clean.append(original_local_path)
        temp_files_to_clean.append(processed_local_path)
        

        # Verify codec of local file_path, downloaded_original and downloaded_processed
        local_original_codec = get_local_file_codec(file_path)
        downloaded_original_codec = get_local_file_codec(original_local_path)
        downloaded_processed_codec = get_local_file_codec(processed_local_path)

        print(f"Local test file codec: Expected '{expected_codecs['original']}', Detected '{local_original_codec}'")
        print(f"Downloaded original file codec: Expected '{expected_codecs['original']}', Detected '{downloaded_original_codec}'")
        print(f"Downloaded processed file codec: Expected '{expected_codecs['processed']}', Detected '{downloaded_processed_codec}'")
        assert expected_codecs['original'] == local_original_codec
        assert expected_codecs['original'] == downloaded_original_codec
        assert expected_codecs['processed'] == downloaded_processed_codec

    finally:
        # Cleanup temporary downloaded files
        for temp_file in temp_files_to_clean:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"Cleaned up temporary file: {temp_file}")
    

def run_e2e_test_for_file(file_path: str, expected_codecs: dict):
    print("\n" + "="*80)
    print(f"STARTING E2E TEST FOR: {file_path}")
    print("="*80)
    
    try:
        # Step 1: Upload
        file_id = test_upload_file(file_path)
        
        # Step 2: Unhappy Path Test:
        test_unhappy_path_download(file_id)
        
        # Step 3: Poll for completion
        test_poll_for_completion(file_id)
        
        # Step 4: Download and verify
        test_download_and_verify_codecs(file_id, file_path, expected_codecs)

        print("\n" + "="*80)
        print(f"e2e tests passed for {file_path}!")
        print("="*80)

    except Exception as e:
        print(f"\nERROR OCCURRED DURING TEST FOR {file_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # check for ffprobe
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("ffprobe not found. Please install ffmpeg on your local machine to run codec checks")
        print("download ffmpeg via `brew install ffmpeg` or `sudo apt install ffmpeg` (Debian/Ubuntu).")
        sys.exit(0) # Exit gracefully if ffprobe isn't there

    for file_path, codecs in TEST_FILES.items():
        if not os.path.exists(file_path):
            print(f"\nERROR: Test file not found at '{file_path}'. Please create the {TESTS_FILES_FOLDER} directory and add your videos.")
            continue
        run_e2e_test_for_file(file_path, codecs)