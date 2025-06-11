from pydantic import BaseModel
from uuid import UUID
from .models import ProcessingStatus

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


    class Config:
        orm_mode = True