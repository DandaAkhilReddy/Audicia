"""
AUDICIA VOICE-TO-SOAP SYSTEM
Pydantic Schemas for API Request/Response Validation
HIPAA-Compliant Data Models
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid

# ==========================================
# REQUEST SCHEMAS
# ==========================================

class VoiceToSOAPRequest(BaseModel):
    """Request schema for voice-to-SOAP conversion"""
    
    doctor_email: str = Field(
        ..., 
        description="Healthcare provider email address",
        example="doctor@hospital.com"
    )
    
    patient_mrn: str = Field(
        ..., 
        description="Patient Medical Record Number",
        min_length=1,
        max_length=50,
        example="MRN-2025-001"
    )
    
    visit_type: Optional[str] = Field(
        default="routine",
        description="Type of medical visit",
        example="routine"
    )
    
    session_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier"
    )
    
    @validator('doctor_email')
    def validate_doctor_email(cls, v):
        """Validate doctor email format"""
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('visit_type')
    def validate_visit_type(cls, v):
        """Validate visit type"""
        valid_types = [
            "routine", "urgent", "emergency", "follow-up", 
            "consultation", "procedure", "post-op"
        ]
        if v and v.lower() not in valid_types:
            raise ValueError(f'Visit type must be one of: {", ".join(valid_types)}')
        return v.lower() if v else "routine"

class PatientContextRequest(BaseModel):
    """Optional patient context for enhanced SOAP generation"""
    
    age: Optional[int] = Field(None, ge=0, le=150, description="Patient age")
    gender: Optional[str] = Field(None, description="Patient gender")
    known_conditions: Optional[List[str]] = Field(
        default_factory=list,
        description="Known medical conditions"
    )
    current_medications: Optional[List[str]] = Field(
        default_factory=list,
        description="Current medications"
    )
    allergies: Optional[List[str]] = Field(
        default_factory=list,
        description="Known allergies"
    )

class ProviderContextRequest(BaseModel):
    """Optional provider context for enhanced SOAP generation"""
    
    specialty: Optional[str] = Field(None, description="Medical specialty")
    department: Optional[str] = Field(None, description="Hospital department")
    license_number: Optional[str] = Field(None, description="Medical license number")

# ==========================================
# RESPONSE SCHEMAS  
# ==========================================

class VitalSignsResponse(BaseModel):
    """Vital signs data structure"""
    
    blood_pressure: Optional[str] = Field(None, example="120/80")
    heart_rate: Optional[str] = Field(None, example="72")
    temperature: Optional[str] = Field(None, example="98.6")
    respiratory_rate: Optional[str] = Field(None, example="16")
    oxygen_saturation: Optional[str] = Field(None, example="98")
    weight: Optional[str] = Field(None, example="150")
    height: Optional[str] = Field(None, example="68")
    bmi: Optional[str] = Field(None, example="22.8")

class SubjectiveResponse(BaseModel):
    """Subjective section of SOAP note"""
    
    chief_complaint: Optional[str] = Field(None, example="Chest pain")
    history_present_illness: Optional[str] = Field(None)
    review_of_systems: Optional[str] = Field(None)
    past_medical_history: Optional[str] = Field(None)
    medications: Optional[str] = Field(None)
    allergies: Optional[str] = Field(None)
    social_history: Optional[str] = Field(None)
    family_history: Optional[str] = Field(None)

class ObjectiveResponse(BaseModel):
    """Objective section of SOAP note"""
    
    vital_signs: Optional[VitalSignsResponse] = Field(None)
    physical_examination: Optional[str] = Field(None)
    laboratory_results: Optional[str] = Field(None)
    imaging_results: Optional[str] = Field(None)

class AssessmentResponse(BaseModel):
    """Assessment section of SOAP note"""
    
    primary_diagnosis: Optional[str] = Field(None, example="Acute chest pain")
    icd10_codes: Optional[List[str]] = Field(default_factory=list, example=["R06.02"])
    differential_diagnoses: Optional[List[str]] = Field(default_factory=list)
    clinical_impression: Optional[str] = Field(None)

class PlanResponse(BaseModel):
    """Plan section of SOAP note"""
    
    medications: Optional[List[str]] = Field(default_factory=list)
    procedures: Optional[List[str]] = Field(default_factory=list)
    laboratory_tests: Optional[List[str]] = Field(default_factory=list)
    imaging_studies: Optional[List[str]] = Field(default_factory=list)
    follow_up: Optional[str] = Field(None)
    patient_education: Optional[str] = Field(None)
    referrals: Optional[List[str]] = Field(default_factory=list)

class QualityMetricsResponse(BaseModel):
    """SOAP note quality assessment metrics"""
    
    overall_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_level: Optional[str] = Field(None, example="excellent")
    detailed_metrics: Optional[Dict[str, float]] = Field(default_factory=dict)
    recommendations: Optional[List[str]] = Field(default_factory=list)

class ProcessingMetadataResponse(BaseModel):
    """AI processing metadata"""
    
    session_id: Optional[str] = Field(None)
    model_used: Optional[str] = Field(None, example="gpt-4-turbo-preview")
    processing_time_seconds: Optional[float] = Field(None, ge=0.0)
    tokens_used: Optional[int] = Field(None, ge=0)
    prompt_tokens: Optional[int] = Field(None, ge=0)
    completion_tokens: Optional[int] = Field(None, ge=0)
    estimated_cost_usd: Optional[float] = Field(None, ge=0.0)
    transcription_length: Optional[int] = Field(None, ge=0)
    timestamp: Optional[float] = Field(None)

class SOAPNoteResponse(BaseModel):
    """Complete SOAP note response"""
    
    id: str = Field(..., description="Unique SOAP note identifier")
    session_id: str = Field(..., description="Session identifier")
    provider_email: str = Field(..., description="Healthcare provider email")
    patient_mrn: str = Field(..., description="Patient MRN")
    
    # SOAP note sections
    subjective: Optional[SubjectiveResponse] = Field(None)
    objective: Optional[ObjectiveResponse] = Field(None)
    assessment: Optional[AssessmentResponse] = Field(None)
    plan: Optional[PlanResponse] = Field(None)
    
    # Transcription data
    transcription: str = Field(..., description="Original transcription text")
    transcription_confidence: str = Field(..., description="Transcription confidence level")
    
    # Processing information
    processing_time_seconds: float = Field(..., ge=0.0, description="Total processing time")
    tokens_used: int = Field(..., ge=0, description="AI tokens consumed")
    estimated_cost_usd: float = Field(..., ge=0.0, description="Estimated processing cost")
    
    # Metadata
    created_at: str = Field(..., description="Creation timestamp")
    status: str = Field(..., description="SOAP note status")
    quality_metrics: Optional[QualityMetricsResponse] = Field(None)
    processing_metadata: Optional[ProcessingMetadataResponse] = Field(None)
    
    class Config:
        """Pydantic model configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TranscriptionResponse(BaseModel):
    """Audio transcription response"""
    
    success: bool = Field(..., description="Transcription success status")
    session_id: str = Field(..., description="Session identifier")
    transcription: str = Field(..., description="Transcribed text")
    confidence_score: str = Field(..., description="Confidence level")
    processing_time_seconds: float = Field(..., ge=0.0)
    word_count: int = Field(..., ge=0)
    medical_terms_detected: int = Field(..., ge=0)
    quality_assessment: Dict[str, Any] = Field(..., description="Quality metrics")
    
    # File metadata
    file_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class HealthCheckResponse(BaseModel):
    """System health check response"""
    
    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    services: Dict[str, str] = Field(..., description="Individual service statuses")

# ==========================================
# ERROR RESPONSE SCHEMAS
# ==========================================

class ErrorResponse(BaseModel):
    """Standard error response format"""
    
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(..., description="Error timestamp")
    session_id: Optional[str] = Field(None, description="Session identifier if available")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional error details")

class ValidationErrorResponse(BaseModel):
    """Validation error response format"""
    
    error: str = Field(..., description="Validation error message")
    status_code: int = Field(422, description="HTTP status code")
    timestamp: str = Field(..., description="Error timestamp")
    validation_errors: List[Dict[str, Any]] = Field(..., description="Detailed validation errors")

# ==========================================
# LIST/PAGINATION SCHEMAS
# ==========================================

class SOAPNoteListRequest(BaseModel):
    """Request schema for listing SOAP notes"""
    
    provider_email: Optional[str] = Field(None, description="Filter by provider email")
    patient_mrn: Optional[str] = Field(None, description="Filter by patient MRN")
    visit_type: Optional[str] = Field(None, description="Filter by visit type")
    status: Optional[str] = Field(None, description="Filter by SOAP note status")
    
    # Date range filtering
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    
    # Pagination
    limit: int = Field(50, ge=1, le=100, description="Number of records to return")
    offset: int = Field(0, ge=0, description="Number of records to skip")
    
    # Sorting
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order (asc/desc)")
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order"""
        if v.lower() not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v.lower()

class SOAPNoteListResponse(BaseModel):
    """Response schema for SOAP note list"""
    
    items: List[SOAPNoteResponse] = Field(..., description="SOAP note items")
    total_count: int = Field(..., ge=0, description="Total number of items")
    page_info: Dict[str, Any] = Field(..., description="Pagination information")

# ==========================================
# AUDIT LOG SCHEMAS
# ==========================================

class AuditLogEntry(BaseModel):
    """Audit log entry for HIPAA compliance"""
    
    id: str = Field(..., description="Audit log entry ID")
    timestamp: str = Field(..., description="Event timestamp")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Resource type affected")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    success: bool = Field(..., description="Action success status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    additional_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

# ==========================================
# UTILITY SCHEMAS
# ==========================================

class APIKeyValidationRequest(BaseModel):
    """API key validation request"""
    
    api_key: str = Field(..., description="API key to validate")
    
class APIKeyValidationResponse(BaseModel):
    """API key validation response"""
    
    valid: bool = Field(..., description="API key validity")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")
    permissions: List[str] = Field(default_factory=list, description="Granted permissions")

# ==========================================
# CONFIGURATION SCHEMAS
# ==========================================

class SystemConfigResponse(BaseModel):
    """System configuration response"""
    
    max_audio_file_size_mb: int = Field(..., description="Maximum audio file size")
    supported_audio_formats: List[str] = Field(..., description="Supported audio formats")
    max_processing_time_seconds: int = Field(..., description="Maximum processing time")
    rate_limits: Dict[str, int] = Field(..., description="API rate limits")

if __name__ == "__main__":
    # Test schema validation
    import json
    
    # Test request schema
    request_data = {
        "doctor_email": "doctor@hospital.com",
        "patient_mrn": "MRN-2025-001",
        "visit_type": "routine"
    }
    
    try:
        request = VoiceToSOAPRequest(**request_data)
        print("✅ Request schema validation passed")
        print(f"Generated session ID: {request.session_id}")
        
    except Exception as e:
        print(f"❌ Request schema validation failed: {e}")
    
    # Test response schema structure
    response_data = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "session_id": "550e8400-e29b-41d4-a716-446655440001",
        "provider_email": "doctor@hospital.com",
        "patient_mrn": "MRN-2025-001",
        "transcription": "Patient presents with chest pain...",
        "transcription_confidence": "high",
        "processing_time_seconds": 15.5,
        "tokens_used": 1200,
        "estimated_cost_usd": 0.036,
        "created_at": "2025-01-06T12:00:00Z",
        "status": "draft"
    }
    
    try:
        response = SOAPNoteResponse(**response_data)
        print("✅ Response schema validation passed")
        
    except Exception as e:
        print(f"❌ Response schema validation failed: {e}")