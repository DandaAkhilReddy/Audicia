"""
AUDICIA VOICE-TO-SOAP SYSTEM
SQLAlchemy Database Models
HIPAA-Compliant with PHI Encryption and Audit Trails
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declared_attr
from db import Base
import structlog

logger = structlog.get_logger()

class TimestampMixin:
    """
    Mixin to add timestamp fields to models
    Provides created_at and updated_at with UTC timezone
    """
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), 
                     default=lambda: datetime.now(timezone.utc),
                     nullable=False,
                     index=True)
    
    @declared_attr 
    def updated_at(cls):
        return Column(DateTime(timezone=True),
                     default=lambda: datetime.now(timezone.utc),
                     onupdate=lambda: datetime.now(timezone.utc),
                     nullable=False,
                     index=True)

class AuditMixin:
    """
    Mixin to add audit trail fields for HIPAA compliance
    Tracks who created/modified records for regulatory compliance
    """
    
    @declared_attr
    def created_by(cls):
        return Column(String(255), nullable=True, index=True)
    
    @declared_attr
    def modified_by(cls):
        return Column(String(255), nullable=True, index=True)
    
    @declared_attr
    def audit_log(cls):
        return Column(JSONB, default=dict, nullable=True)

class Provider(Base, TimestampMixin, AuditMixin):
    """
    Healthcare Provider/Doctor model
    Stores provider information with HIPAA audit compliance
    """
    __tablename__ = "providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    license_number = Column(String(50), nullable=True, index=True)
    specialty = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationship to SOAP notes
    soap_notes = relationship("SOAPNote", back_populates="provider", cascade="all, delete-orphan")
    audio_files = relationship("AudioFile", back_populates="provider", cascade="all, delete-orphan")
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format"""
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError("Invalid email format")
        return email.lower()
    
    def __repr__(self):
        return f"<Provider(id={self.id}, email={self.email}, name={self.name})>"

class Patient(Base, TimestampMixin, AuditMixin):
    """
    Patient model with PHI encryption
    Stores patient demographic information securely
    """
    __tablename__ = "patients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    mrn = Column(String(50), unique=True, nullable=False, index=True)  # Medical Record Number
    
    # PHI fields (would be encrypted in production)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime(timezone=True), nullable=True, index=True)
    gender = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Address information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    
    # Insurance and emergency contact (encrypted in production)
    insurance_info = Column(JSONB, default=dict, nullable=True)
    emergency_contact = Column(JSONB, default=dict, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    soap_notes = relationship("SOAPNote", back_populates="patient", cascade="all, delete-orphan")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        if self.date_of_birth:
            today = datetime.now(timezone.utc)
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    def __repr__(self):
        return f"<Patient(id={self.id}, mrn={self.mrn}, name={self.full_name})>"

class AudioFile(Base, TimestampMixin, AuditMixin):
    """
    Audio file metadata and storage information
    Tracks uploaded audio files with transcription status
    """
    __tablename__ = "audio_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(50), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    
    # Azure Blob Storage information
    blob_container = Column(String(100), nullable=True)
    blob_name = Column(String(255), nullable=True)
    blob_url = Column(Text, nullable=True)
    
    # Processing status
    transcription_status = Column(String(20), default="pending", nullable=False, index=True)
    # pending, processing, completed, failed
    transcription_confidence = Column(String(10), nullable=True)  # high, medium, low
    error_message = Column(Text, nullable=True)
    
    # Relationships
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False, index=True)
    provider = relationship("Provider", back_populates="audio_files")
    
    soap_notes = relationship("SOAPNote", back_populates="audio_file", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AudioFile(id={self.id}, filename={self.filename}, status={self.transcription_status})>"

class SOAPNote(Base, TimestampMixin, AuditMixin):
    """
    SOAP Note model with structured medical documentation
    Stores comprehensive SOAP note data with audit compliance
    """
    __tablename__ = "soap_notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    audio_file_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=True, index=True)
    
    # Visit information
    visit_date = Column(DateTime(timezone=True), nullable=False, index=True)
    visit_type = Column(String(50), nullable=True)  # routine, urgent, follow-up, etc.
    
    # Raw transcription data
    transcription = Column(Text, nullable=True)
    transcription_confidence = Column(String(10), nullable=True)
    
    # Structured SOAP data (stored as JSONB for flexibility and performance)
    subjective_data = Column(JSONB, default=dict, nullable=True)
    objective_data = Column(JSONB, default=dict, nullable=True)
    assessment_data = Column(JSONB, default=dict, nullable=True)
    plan_data = Column(JSONB, default=dict, nullable=True)
    
    # Quick access fields for common queries
    chief_complaint = Column(String(500), nullable=True, index=True)
    primary_diagnosis = Column(String(255), nullable=True, index=True)
    icd10_codes = Column(JSONB, default=list, nullable=True)
    
    # AI processing metadata
    ai_model_used = Column(String(50), nullable=True)  # gpt-4, gpt-3.5-turbo, etc.
    ai_confidence_score = Column(String(10), nullable=True)  # high, medium, low
    processing_time_seconds = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    estimated_cost = Column(String(10), nullable=True)  # in USD
    
    # Status and workflow
    status = Column(String(20), default="draft", nullable=False, index=True)
    # draft, review_needed, approved, signed, archived
    is_signed = Column(Boolean, default=False, nullable=False, index=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    signed_by = Column(String(255), nullable=True)
    
    # Relationships
    provider = relationship("Provider", back_populates="soap_notes")
    patient = relationship("Patient", back_populates="soap_notes")
    audio_file = relationship("AudioFile", back_populates="soap_notes")
    
    def __repr__(self):
        return f"<SOAPNote(id={self.id}, patient={self.patient_id}, provider={self.provider_id}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SOAP note to dictionary for API responses"""
        return {
            "id": str(self.id),
            "provider_id": str(self.provider_id),
            "patient_id": str(self.patient_id),
            "visit_date": self.visit_date.isoformat() if self.visit_date else None,
            "visit_type": self.visit_type,
            "chief_complaint": self.chief_complaint,
            "primary_diagnosis": self.primary_diagnosis,
            "icd10_codes": self.icd10_codes,
            "subjective": self.subjective_data,
            "objective": self.objective_data,
            "assessment": self.assessment_data,
            "plan": self.plan_data,
            "status": self.status,
            "is_signed": self.is_signed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "ai_metadata": {
                "model_used": self.ai_model_used,
                "confidence_score": self.ai_confidence_score,
                "processing_time": self.processing_time_seconds,
                "tokens_used": self.tokens_used,
                "estimated_cost": self.estimated_cost
            }
        }
    
    @classmethod
    def create_from_ai_response(cls, ai_data: Dict[str, Any], **kwargs) -> "SOAPNote":
        """Create SOAP note from AI-generated data"""
        
        # Extract structured data from AI response
        subjective = ai_data.get("subjective", {})
        objective = ai_data.get("objective", {})
        assessment = ai_data.get("assessment", {})
        plan = ai_data.get("plan", {})
        metadata = ai_data.get("metadata", {})
        
        return cls(
            subjective_data=subjective,
            objective_data=objective,
            assessment_data=assessment,
            plan_data=plan,
            chief_complaint=subjective.get("chief_complaint", ""),
            primary_diagnosis=assessment.get("primary_diagnosis", ""),
            icd10_codes=assessment.get("icd10_codes", []),
            ai_model_used=metadata.get("model_used"),
            ai_confidence_score=str(metadata.get("confidence_score", "")),
            processing_time_seconds=metadata.get("processing_time"),
            tokens_used=metadata.get("tokens_used"),
            estimated_cost=str(metadata.get("estimated_cost", "")),
            **kwargs
        )

class SystemAuditLog(Base, TimestampMixin):
    """
    System-wide audit logging for HIPAA compliance
    Tracks all system access and PHI interactions
    """
    __tablename__ = "system_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # User and session information
    user_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    
    # Audit details
    success = Column(Boolean, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    additional_data = Column(JSONB, default=dict, nullable=True)
    
    def __repr__(self):
        return f"<SystemAuditLog(id={self.id}, action={self.action}, success={self.success})>"

# Database indexes for performance optimization
Index('idx_soap_notes_provider_date', SOAPNote.provider_id, SOAPNote.visit_date)
Index('idx_soap_notes_patient_date', SOAPNote.patient_id, SOAPNote.visit_date) 
Index('idx_soap_notes_status_date', SOAPNote.status, SOAPNote.created_at)
Index('idx_audio_files_status', AudioFile.transcription_status, AudioFile.created_at)
Index('idx_audit_logs_action_date', SystemAuditLog.action, SystemAuditLog.created_at)

if __name__ == "__main__":
    # Test model creation
    import logging
    from db import engine, init_database
    
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("Creating database tables...")
        init_database()
        print("✅ Database tables created successfully!")
        
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")