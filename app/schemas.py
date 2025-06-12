from pydantic import BaseModel
from uuid import UUID
from .models import ProcessingStatus, Codec
from typing import Optional

class UploadResponse(BaseModel):
    file_id: UUID
    file_name: str
    processing_status: ProcessingStatus
    
    class Config:
        orm_mode = True

class StatusResponse(BaseModel):
    file_id: UUID
    file_name: str
    processing_status: ProcessingStatus

    original_codec: Optional[Codec] = None
    target_codec: Optional[Codec] = None
    processing_time: Optional[float] = None

    class Config:
        from_attributes = True

class DownloadURLResponse(BaseModel):
    download_url: str
