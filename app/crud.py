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
