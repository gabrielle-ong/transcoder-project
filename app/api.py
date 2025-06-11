import boto3
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from .database import init_db, get_db
# db_init race condition - need to import models so that init_db creates Files and Transactions models
from . import models, schemas, crud
from uuid import uuid4, UUID
import os

# Create DB tables on startup, checks that db container is ready (race condition bug)
init_db()

app = FastAPI()

@app.get("/")
def root():
    return "Hello HTX!!"

@app.post("/upload", response_model=schemas.UploadResponse)
def upload_file(db: Session = Depends(get_db), file: UploadFile = File(...)):
    s3_client = boto3.client("s3")
    file_id = uuid4()
    name_stem, file_extension = os.path.splitext(file.filename)
    s3_key = f"{name_stem}-{file_id}{file_extension}" # original_filename-uuid.ext
    bucket_name = os.getenv("S3_RAW_BUCKET")
    raw_file_url = f"s3://{bucket_name}/{s3_key}"

    # 1. Create new File DB record; create new Transaction record type=Upload
    db_file = crud.create_file_record(db, file_id, file.filename, raw_file_url)
    crud.create_transaction(db, file_id, models.TransactionType.UPLOAD, details="Upload started by user")

    try:
        s3_client.upload_fileobj(file.file, bucket_name, s3_key)
    except Exception as e:
        # 2. Handle Failed Transaction
        crud.update_file_status(db, file_id, models.ProcessingStatus.FAILED)
        crud.create_transaction(db, file_id, models.TransactionType.FAILURE, details=f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")

    # 3. Handle File upload complete, pending in queue
    crud.update_file_status(db, file_id, models.ProcessingStatus.PENDING)
    crud.create_transaction(db, file_id, models.TransactionType.PENDING, details="File upload complete, awaiting transcoding")

    return db_file