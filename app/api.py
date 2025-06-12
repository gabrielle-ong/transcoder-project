import os
import boto3
import logging
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from urllib.parse import urlparse
from typing import Optional
from . import models, schemas, crud
from .database import get_db


### To view s3 Multipart upload
# eg DEBUG:botocore.endpoint:Making request for OperationModel(name=CompleteMultipartUpload) with params: {'url_path': '...'
# logging.basicConfig(level=logging.INFO)
# logging.getLogger('boto3').setLevel(logging.DEBUG)
# logging.getLogger('botocore').setLevel(logging.DEBUG)

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

# download from s3 presigned url
def _get_presigned_s3_url(s3_url: str, download_filename: Optional[str]) -> StreamingResponse:
    s3_endpoint_url = os.getenv("S3_ENDPOINT_URL") or None
    s3_client = boto3.client("s3", endpoint_url=s3_endpoint_url)

    s3_path = urlparse(s3_url, allow_fragments=False)
    bucket_name = s3_path.netloc  # The bucket name
    s3_key = s3_path.path.lstrip('/')

    if not bucket_name or not s3_key:
        raise ValueError("Invalid S3 URL provided.")
    
    params = {'Bucket': bucket_name, 'Key': s3_key}
    if download_filename:
        params['ResponseContentDisposition'] = f'attachment; filename="{download_filename}"'

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=3600  # 1h
        )
        return url
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Could not generate presigned URL: {e}")

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

    # Multipart Upload configs
    MB = 1024 * 1024
    config = TransferConfig(
        multipart_threshold = 4 * MB,  # 4MB; Production numbers: 20MB
        max_concurrency = 5,
        multipart_chunksize = 2 * MB, # 2MB; Production numbers: 10MB
        use_threads=True
    )
    #2. Upload to S3
    try:
        print(f"Uploading {s3_key} file to S3 {raw_file_url}...")
        s3_client.upload_fileobj(file.file, bucket_name, s3_key, Config=config)
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

@app.get("/upload/{file_id}/download/original", response_model=schemas.DownloadURLResponse)
def download_original_file(file_id: UUID, db: Session = Depends(get_db)):
    db_file = _get_file(db, file_id)
    url = _get_presigned_s3_url(db_file.raw_file_url, db_file.file_name)
    return {"download_url": url}

@app.get("/upload/{file_id}/download/processed", response_model=schemas.DownloadURLResponse)
def download_processed_file(file_id: UUID, db: Session = Depends(get_db)):
    db_file = _get_file(db, file_id)
    
    if db_file.processing_status != models.ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=404, 
            detail=f"Processed file not available. Current File status: {db_file.processing_status}"
        )
    download_filename = f"processed-{db_file.file_name}"
    url = _get_presigned_s3_url(db_file.processed_file_url, download_filename)
    return {"download_url": url}