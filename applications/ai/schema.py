from typing import List, Optional
from pydantic import BaseModel, Field


class EquipmentScanRequest(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image data")
    prompt: Optional[str] = Field(None, description="Optional custom prompt for the AI")


class EquipmentDetection(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    description: Optional[str] = None


class EquipmentScanResponse(BaseModel):
    success: bool
    equipment_detected: List[EquipmentDetection]
    primary_equipment: Optional[str] = None
    error_message: Optional[str] = None


class EquipmentInfoRequest(BaseModel):
    equipment_name: str = Field(..., description="Name of the equipment to get information about")


class EquipmentInfo(BaseModel):
    name: str
    category: Optional[str] = None
    muscle_groups: List[str] = []
    description: Optional[str] = None
    common_exercises: List[str] = []


class EquipmentInfoResponse(BaseModel):
    success: bool
    equipment: Optional[EquipmentInfo] = None
    error_message: Optional[str] = None


class EquipmentVerifyRequest(BaseModel):
    equipment_name: str = Field(..., description="Name of the equipment to verify")


class EquipmentVerifyResponse(BaseModel):
    success: bool
    is_match: bool
    message: str
    confidence: Optional[float] = None
