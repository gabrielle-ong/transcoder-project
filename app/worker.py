import boto3
from botocore.exceptions import ClientError
import os
import subprocess
import time
import json
from uuid import UUID
from sqlalchemy.orm import Session

from . import crud, models
from .models import Codec
from .database import init_db, SessionLocal

# Main loop to poll SQS queue and process messages
def process_messages():
    sqs_client = boto3.client("sqs", endpoint_url=os.getenv("SQS_ENDPOINT_URL"), region_name=os.getenv("REGION_NAME"))
    queue_url = os.getenv("SQS_QUEUE_URL")

    print("Worker started, polling for messages...")
    while True:
        response = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=10)
        if "Messages" in response:
            message = response["Messages"][0]
            body = json.loads(message['Body'])
            print(body)
            # Ignore s3:TestEvent
            if body.get("Event") == "s3:TestEvent":
                sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
                continue
            process_single_message(message)
            sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])


def process_single_message(message: dict):
    db = SessionLocal()
    s3_client = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT_URL"))
    raw_bucket = os.getenv("S3_RAW_BUCKET")
    processed_bucket = os.getenv("S3_PROCESSED_BUCKET")
    file_id = None

    try: 
        body = json.loads(message['Body'])
        s3_key = body['Records'][0]['s3']['object']['key'] # s3key is original_filename-uuid
        key_without_ext, _ = os.path.splitext(s3_key)
        uuid_str = key_without_ext[-36:]
        file_id = UUID(uuid_str) 

        ## Idempotency check - Get File Status, discard message if File status = PROCESSING
        ## to avoid case where message queue triggers transcoding multiple times when file is already processing (but not yet completed)
        db_file = crud.get_file(db, file_id)
        if not db_file:
            print(f"File ID {file_id} not found in database. Discarding message.")
            return # Exit the function, the message will be deleted
        current_status = db_file.processing_status
        if current_status == models.ProcessingStatus.PENDING: # New transcoding job
            transcode_file(db, file_id, s3_key, s3_client, raw_bucket, processed_bucket)
        else: # is already being processed or complete, ignore
            print(f"Skipping duplicate message for file_id: {file_id}. Current status: {current_status}")
    except Exception as e:
        # If file_id was extracted, we can log failure against it
        # Any failure from codec format, S3 download, ffmpeg transcoding, s3 upload
        if file_id:
            handle_processing_failure(db, file_id, e)
        else:
            print(f"Failed to parse message or extract file_id: {message['Body']}")
    finally:
        db.close()

def get_video_codec(file_path: str) -> str: # returns `h264` or `hevc` (for h265)
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name", "-of", "compact=p=0:nk=1",
        "-i", file_path,
    ]
    try:
        print(f"Running ffprobe command: {' '.join(command)}")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        codec_str = result.stdout.strip()
        print("codec", codec_str)
        return Codec(codec_str)
    except ValueError:
        raise RuntimeError(f"Unsupported codec detected: {codec_str}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe get codec failed: {e.stderr}")
    
def ffmpeg_popen(command):
    # prints out process output instead of subprocess.run which waits till it finishes
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, bufsize=1, universal_newlines=True)
        for line in process.stdout:
            print(f"[ffmpeg] {line.strip()}")
        # Wait for the process to complete and check its return code
        process.wait()
        if process.returncode != 0:
            # If ffmpeg failed, raise an error
            raise RuntimeError(f"FFmpeg transcode to h265 failed with exit code {process.returncode}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg process failed: {e.stderr}")

def transcode_to_h264(input_path: str, output_path: str):
    print(f"Transcoding from HEVC to H.264")
    command = [
        "ffmpeg", "-i", input_path, "-c:v", "libx264", # libx264 encoder
        "-preset", "fast", "-crf", "23", "-c:a", "copy", output_path
    ]
    ffmpeg_popen(command)
    
def transcode_to_h265(input_path: str, output_path: str):
    print(f"Transcoding from H.264 to HEVC")
    command = [
        "ffmpeg", "-i", input_path, "-c:v", "libx265", # libx265 encoder
        "-preset", "fast", "-crf", "28", "-vtag", "hvc1", "-c:a", "copy", output_path
    ]
    ffmpeg_popen(command)
    

def transcode_file(db: Session, file_id: UUID, s3_key: str, s3_client, raw_bucket: str, processed_bucket: str):
    print(f"Transcoding file: {s3_key}")
    filename = os.path.basename(s3_key)
    input_path = f"/tmp/{filename}"
    output_path = f"/tmp/processed-{filename}"

    try:
        # Start transaction
        print("DB updating file status and transactions to processing")
        crud.update_file_status(db, file_id, models.ProcessingStatus.PROCESSING)
        crud.create_transaction(db, file_id, models.TransactionType.PROCESSING, details="Started processing")
        start_time = time.time()
        print("start time", start_time)

        # Download, process, upload
        try:
            print(f"Downloading s3://{raw_bucket}/{s3_key} to {input_path}")
            s3_client.download_file(raw_bucket, s3_key, input_path)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            raise RuntimeError(f"S3 Download Failed (Error: {error_code})") from e
        
        original_codec = get_video_codec(input_path)

        if original_codec == Codec.H264:
            target_codec = Codec.HEVC
            transcode_to_h265(input_path, output_path)
        elif original_codec == Codec.HEVC:
            target_codec = Codec.H264
            transcode_to_h264(input_path, output_path)
        else:
            raise RuntimeError(f"Unsupported codec '{original_codec}' for transcoding.")
        
        try:
            print(f"Uploading transcoded file {output_path} to s3://{processed_bucket}/{s3_key}")
            s3_client.upload_file(output_path, processed_bucket, s3_key)
        except ClientError as e:
            # If the bucket doesn't exist or we don't have permission, catch it here.
            error_code = e.response.get("Error", {}).get("Code")
            raise RuntimeError(f"S3 Upload Failed (Error: {error_code})") from e

        # Finalize
        print("finalizing")
        processing_time = time.time() - start_time
        processed_url = f"s3://{processed_bucket}/{s3_key}"
        crud.finalize_file_on_completion(db, file_id, processed_url, processing_time, original_codec, target_codec)
        crud.create_transaction(db, file_id, models.TransactionType.COMPLETION, f"Completed in {processing_time:.2f}s")
        print(f"Successfully processed {file_id}")

    finally:
        # Cleanup local temp files
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)


def handle_processing_failure(db: Session, file_id: UUID, error: Exception):
    error_details = f"Processing failed: {str(error)}"
    print(error_details)
    crud.update_file_status(db, file_id, models.ProcessingStatus.FAILED)
    crud.create_transaction(db, file_id, models.TransactionType.FAILURE, details=f"Upload failed: {str(error_details)}")

if __name__ == "__main__":
    init_db()
    process_messages()
