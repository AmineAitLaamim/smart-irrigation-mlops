from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)

class UserResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str
    is_admin: bool = False
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    full_name: Optional[str] = Field(None, min_length=1)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ZoneBase(BaseModel):
    zone_name: str
    soil_type: str
    crop_type: str
    moisture_min: float
    moisture_max: float
    active: bool = True

class ZoneCreate(ZoneBase):
    zone_id: Optional[str] = None # Make it optional so we can auto-generate if not provided

class ZoneUpdate(BaseModel):
    zone_name: Optional[str] = None
    soil_type: Optional[str] = None
    crop_type: Optional[str] = None
    moisture_min: Optional[float] = None
    moisture_max: Optional[float] = None
    active: Optional[bool] = None

class ZoneResponse(ZoneBase):
    zone_id: str
    owner_id: Optional[UUID] = None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ZoneAssignment(BaseModel):
    owner_id: UUID
