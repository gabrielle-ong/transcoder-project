import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .database import init_db, get_db
# db_init race condition - need to import models so that init_db creates Files and Transactions models
from . import models, schemas, crud
from uuid import uuid4, UUID
import os
from urllib.parse import urlparse


# Create DB tables on startup, checks that db container is ready (race condition bug)
init_db()

app = FastAPI()

@app.get("/")
def root():
    return "Hello HTX!!"

#### Helper functions #####

# _get_file
def _get_file(db: Session, file_id: UUID) -> models.Files:
    db_file = crud.get_file(db, file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found.")
    return db_file

# to stream S3 file
def _stream_s3_file(s3_url: str, download_filename: str)-> StreamingResponse:
    s3_endpoint_url = os.getenv("S3_ENDPOINT_URL") or None
    s3_client = boto3.client("s3", endpoint_url=s3_endpoint_url)

    try:
        s3_path = urlparse(s3_url, allow_fragments=False)
        bucket_name = s3_path.netloc  # The bucket name is the "netloc" part
        s3_key = s3_path.path.lstrip('/')  # The key is the path, minus the leading slash

        if not bucket_name or not s3_key:
            raise ValueError("Invalid S3 URL provided.")

        s3_object = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        
        return StreamingResponse(
            s3_object['Body'].iter_chunks(),
            media_type='video/mp4',
            headers={"Content-Disposition": f'attachment; filename="{download_filename}"'}
        )
    except (ClientError, ValueError) as e:
        error_detail = str(e)
        if isinstance(e, ClientError) and e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(status_code=404, detail=f"No such file in S3 processed bucket: {s3_key}")
        
        raise HTTPException(status_code=500, detail=f"Error streaming from S3: {error_detail}")
 
 #### end of helper functions #####   

@app.post("/upload", response_model=schemas.UploadResponse)
def upload_file(db: Session = Depends(get_db), file: UploadFile = File(...)):
    s3_endpoint_url = os.getenv("S3_ENDPOINT_URL") or None
    s3_client = boto3.client("s3", endpoint_url=s3_endpoint_url)
    file_id = uuid4()
    name_stem, file_extension = os.path.splitext(file.filename)
    s3_key = f"{name_stem}-{file_id}{file_extension}" # original_filename-uuid.ext
    bucket_name = os.getenv("S3_RAW_BUCKET")
    raw_file_url = f"s3://{bucket_name}/{s3_key}"

    # 1. Create new File DB record; create new Transaction record type=Upload
    db_file = crud.create_file_record(db, file_id, file.filename, raw_file_url) #File processing status = PENDING on creation
    crud.create_transaction(db, file_id, models.TransactionType.UPLOAD, details="Upload started by user")

    #2. Upload to S3
    try:
        s3_client.upload_fileobj(file.file, bucket_name, s3_key)
    except Exception as e:
        crud.update_file_status(db, file_id, models.ProcessingStatus.FAILED)
        crud.create_transaction(db, file_id, models.TransactionType.FAILURE, details=f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")

    # 3. Create transaction, pending in queue
    crud.create_transaction(db, file_id, models.TransactionType.PENDING, details="File upload complete, awaiting transcoding")

    return db_file

@app.get("/upload/{file_id}/status", response_model=schemas.StatusResponse)
def get_status(file_id: UUID, db: Session = Depends(get_db)):
    db_file = _get_file(db, file_id)
    return db_file

@app.get("/upload/{file_id}/download/original")
def download_original_file(file_id: UUID, db: Session = Depends(get_db)):
    db_file = _get_file(db, file_id)
    return _stream_s3_file(db_file.raw_file_url, db_file.file_name)

@app.get("/upload/{file_id}/download/processed")
def download_processed_file(file_id: UUID, db: Session = Depends(get_db)):
    db_file = _get_file(db, file_id)
    
    if db_file.processing_status != models.ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=404, 
            detail=f"Processed file not available. Current File status: {db_file.processing_status}"
        )

    download_filename = f"processed-{db_file.file_name}"
    return _stream_s3_file(db_file.processed_file_url, download_filename)