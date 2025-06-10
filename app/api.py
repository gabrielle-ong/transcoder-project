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
    return "Hello, World!"

@app.post("/upload", response_model=schemas.UploadResponse)
def upload_file(db: Session = Depends(get_db), file: UploadFile = File(...)):
    s3_client = boto3.client("s3")
    file_id = uuid4()
    bucket_name = os.getenv("S3_RAW_BUCKET")
    s3_key = str(file_id)
    raw_file_url = f"s3://{bucket_name}/{s3_key}"

    try:
        s3_client.upload_fileobj(file.file, bucket_name, s3_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")

    db_file = crud.create_file_record(db, file_id, file.filename, raw_file_url)
    crud.create_transaction(db, file_id, models.TransactionType.UPLOAD)

    return db_file