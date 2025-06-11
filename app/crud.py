from sqlalchemy.orm import Session
from uuid import UUID

from . import models

def create_file_record(db: Session, file_id: UUID, file_name: str, raw_file_url: str):
    db_file = models.Files(
        file_id=file_id,
        file_name=file_name,
        raw_file_url=raw_file_url,
        processing_status='PENDING' # Default status
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def create_transaction(db: Session, file_id: UUID, trans_type: models.TransactionType, details: str = None):
    db_transaction = models.Transactions(
        file_id=file_id,
        type=trans_type,
        details=details
    )
    db.add(db_transaction)
    db.commit()


def update_file_status(db: Session, file_id: UUID, status: models.ProcessingStatus):
    db_file = get_file(db, file_id)
    if db_file:
        db_file.processing_status = status
        db.commit()

def get_file(db: Session, file_id: UUID):
    return db.query(models.Files).filter(models.Files.file_id == file_id).first()

def finalize_file_on_completion(db: Session, file_id: UUID, processed_url: str, processing_time: float, original_codec: str, target_codec: str):
    db_file = get_file(db, file_id)
    if db_file:
        db_file.processing_status = models.ProcessingStatus.COMPLETED
        db_file.processed_file_url = processed_url
        db_file.original_codec = original_codec
        db_file.target_codec = target_codec
        db_file.processing_time = processing_time
        db.commit()