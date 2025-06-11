from sqlalchemy import Column, String, DateTime, func, Enum, Float
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from .database import Base

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Codec(str, enum.Enum):
    H264 = "h264"
    HEVC = "hevc" # aka h265

class Files(Base):
    __tablename__ = "files"
    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String, index=True)
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    raw_file_url = Column(String)
    processed_file_url = Column(String, nullable=True)

    original_codec = Column(Enum(Codec), nullable=True)
    target_codec = Column(Enum(Codec), nullable=True)
    processing_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())

class TransactionType(str, enum.Enum):
    UPLOAD = "upload"
    PENDING = "pending" # queued
    PROCESSING = "processing" #transcoding
    COMPLETION = "completion"
    FAILURE = "failure"

class Transactions(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), index=True)
    type = Column(Enum(TransactionType))
    timestamp = Column(DateTime, default=func.now())
    details = Column(String, nullable=True)