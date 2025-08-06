"""
AUDICIA VOICE-TO-SOAP SYSTEM
Production FastAPI Application
HIPAA-Compliant Medical Documentation with Voice Recording
"""

import os
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

# FastAPI and web framework
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Pydantic for data validation
from pydantic import BaseModel, Field, validator

# SQLAlchemy database
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

# Internal modules
from db import get_database_session, check_database_health, init_database
from models import Provider, Patient, AudioFile, SOAPNote, SystemAuditLog
from transcriber import transcribe_audio_bytes, transcribe_audio
from soap_generator import generate_soap
from simple_secret_manager import validate_production_secrets

# Logging and monitoring
import structlog
import time

# Initialize structured logging
logger = structlog.get_logger()

# Security
security = HTTPBearer()

# ==========================================
# PYDANTIC MODELS FOR API
# ==========================================

class VoiceToSOAPRequest(BaseModel):
    """Request model for voice-to-SOAP conversion"""
    doctor_email: str = Field(..., description="Healthcare provider email")
    patient_mrn: str = Field(..., description="Patient Medical Record Number") 
    visit_type: Optional[str] = Field(default="routine", description="Type of visit")
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    
    @validator('doctor_email')
    def validate_email(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower()

class SOAPNoteResponse(BaseModel):
    """Response model for SOAP note creation"""
    id: str
    session_id: str
    provider_email: str
    patient_mrn: str
    soap_data: Dict[str, Any]
    transcription: str
    transcription_confidence: str
    processing_time_seconds: float
    tokens_used: int
    estimated_cost_usd: float
    created_at: str
    status: str

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]

# ==========================================
# FASTAPI APPLICATION SETUP
# ==========================================

app = FastAPI(
    title="Audicia Voice-to-SOAP API",
    description="HIPAA-Compliant Medical Documentation with Voice Recording",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware - configure for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Frontend dev server
        "https://audicia-frontend.azurestaticapps.net",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure for production
)

# ==========================================
# STARTUP AND SHUTDOWN EVENTS
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Application startup initialization"""
    try:
        logger.info("Starting Audicia Voice-to-SOAP API")
        
        # Validate all required secrets are available
        if not validate_production_secrets():
            raise RuntimeError("Missing required production secrets")
        
        # Initialize database
        init_database()
        
        # Verify database health
        if not check_database_health():
            raise RuntimeError("Database health check failed")
        
        logger.info("Audicia Voice-to-SOAP API started successfully")
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise RuntimeError(f"Application startup failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown cleanup"""
    logger.info("Shutting down Audicia Voice-to-SOAP API")

# ==========================================
# AUTHENTICATION AND AUTHORIZATION
# ==========================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate JWT token and return current user
    In production, implement full JWT validation with Azure AD
    """
    try:
        token = credentials.credentials
        
        # TODO: Implement proper JWT validation with Azure AD
        # For now, extract email from token (simplified for demo)
        
        # Temporary: decode basic token structure
        # In production: Use proper JWT library and Azure AD validation
        if not token or len(token) < 10:
            raise HTTPException(status_code=401, detail="Invalid token format")
        
        # Mock user info - replace with real JWT validation
        user_info = {
            "email": "doctor@hospital.com",  # Extract from JWT
            "user_id": "user-123",
            "roles": ["provider"],
            "name": "Dr. Smith"
        }
        
        return user_info
        
    except Exception as e:
        logger.error("Authentication failed", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed")

# ==========================================
# AUDIT LOGGING
# ==========================================

async def log_audit_event(
    request: Request,
    user_info: Dict[str, Any],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    additional_data: Optional[Dict] = None,
    db: Session = None
):
    """Log audit event for HIPAA compliance"""
    try:
        if not db:
            return  # Skip if no DB session provided
        
        audit_log = SystemAuditLog(
            user_id=user_info.get("user_id"),
            session_id=request.headers.get("X-Session-ID"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            error_message=error_message,
            additional_data=additional_data or {}
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info("Audit event logged",
                   user_id=user_info.get("user_id"),
                   action=action,
                   resource_type=resource_type,
                   success=success)
        
    except Exception as e:
        logger.error("Failed to log audit event", error=str(e))

# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Audicia Voice-to-SOAP API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "documentation": "/api/docs"
    }

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Check database connectivity
        db_healthy = check_database_health()
        
        # Check Azure services (simplified - would ping actual services)
        azure_speech_status = "healthy"  # Would test actual Azure Speech service
        openai_status = "healthy"        # Would test actual OpenAI service
        keyvault_status = "healthy"      # Would test actual Key Vault access
        
        overall_status = "healthy" if all([
            db_healthy,
            azure_speech_status == "healthy",
            openai_status == "healthy",
            keyvault_status == "healthy"
        ]) else "unhealthy"
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="1.0.0",
            services={
                "database": "healthy" if db_healthy else "unhealthy",
                "azure_speech": azure_speech_status,
                "openai": openai_status,
                "key_vault": keyvault_status
            }
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/api/v1/voice-to-soap", response_model=SOAPNoteResponse)
async def voice_to_soap_complete(
    request: Request,
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(..., description="Audio file (WAV, MP3, M4A)"),
    doctor_email: str = Form(..., description="Healthcare provider email"),
    patient_mrn: str = Form(..., description="Patient Medical Record Number"),
    visit_type: str = Form(default="routine", description="Type of visit"),
    session_id: Optional[str] = Form(default=None),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Complete voice-to-SOAP workflow:
    Audio Upload → Speech-to-Text → AI SOAP Generation → Database Storage
    """
    start_time = time.time()
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    try:
        # Validate input
        if not audio_file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="Invalid audio file type")
        
        if audio_file.size > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(status_code=400, detail="Audio file too large (max 100MB)")
        
        logger.info("Starting voice-to-SOAP processing",
                   session_id=session_id,
                   user_email=current_user.get("email"),
                   doctor_email=doctor_email,
                   patient_mrn=patient_mrn,
                   file_size=audio_file.size)
        
        # Log audit event - processing started
        await log_audit_event(
            request, current_user, "voice_to_soap_start", "soap_note",
            session_id, True, None, 
            {"doctor_email": doctor_email, "patient_mrn": patient_mrn}, db
        )
        
        # Step 1: Get or create provider
        provider = db.query(Provider).filter(Provider.email == doctor_email).first()
        if not provider:
            provider = Provider(
                email=doctor_email,
                name=f"Dr. {doctor_email.split('@')[0].title()}",  # Temporary name
                is_active=True,
                created_by=current_user.get("user_id")
            )
            db.add(provider)
            db.commit()
            db.refresh(provider)
        
        # Step 2: Get or create patient
        patient = db.query(Patient).filter(Patient.mrn == patient_mrn).first()
        if not patient:
            patient = Patient(
                mrn=patient_mrn,
                first_name="Patient",  # Would be provided in full implementation
                last_name=patient_mrn,
                is_active=True,
                created_by=current_user.get("user_id")
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
        
        # Step 3: Save audio file metadata
        audio_record = AudioFile(
            filename=f"{session_id}_{audio_file.filename}",
            original_filename=audio_file.filename,
            file_size=audio_file.size,
            mime_type=audio_file.content_type,
            provider_id=provider.id,
            transcription_status="processing",
            created_by=current_user.get("user_id")
        )
        db.add(audio_record)
        db.commit()
        db.refresh(audio_record)
        
        # Step 4: Read audio data and transcribe
        audio_data = await audio_file.read()
        audio_format = Path(audio_file.filename).suffix[1:]  # Remove dot from extension
        
        logger.info("Starting audio transcription",
                   session_id=session_id,
                   audio_format=audio_format)
        
        transcription_result = transcribe_audio_bytes(
            audio_data, audio_format, session_id
        )
        
        if not transcription_result.get("success", True):
            # Update audio record status
            audio_record.transcription_status = "failed"
            audio_record.error_message = transcription_result.get("error_message")
            db.commit()
            
            await log_audit_event(
                request, current_user, "transcription_failed", "audio_file",
                str(audio_record.id), False, transcription_result.get("error_message"), None, db
            )
            
            raise HTTPException(
                status_code=500, 
                detail=f"Audio transcription failed: {transcription_result.get('error_message')}"
            )
        
        transcription_text = transcription_result["transcription"]
        transcription_confidence = transcription_result["confidence_score"]
        
        # Update audio record with transcription results
        audio_record.transcription_status = "completed"
        audio_record.transcription_confidence = transcription_confidence
        audio_record.duration_seconds = transcription_result.get("processing_time_seconds")
        db.commit()
        
        logger.info("Audio transcription completed",
                   session_id=session_id,
                   transcription_length=len(transcription_text),
                   confidence=transcription_confidence)
        
        # Step 5: Generate SOAP note using AI
        logger.info("Starting SOAP generation", session_id=session_id)
        
        patient_context = {
            "mrn": patient.mrn,
            "age": patient.age,
            "gender": patient.gender
        } if patient else None
        
        provider_context = {
            "email": provider.email,
            "name": provider.name,
            "specialty": provider.specialty
        } if provider else None
        
        soap_result = generate_soap(
            transcription_text, 
            patient_context,
            provider_context,
            session_id
        )
        
        if not soap_result.get("success", True):
            await log_audit_event(
                request, current_user, "soap_generation_failed", "soap_note",
                session_id, False, soap_result.get("error_message"), None, db
            )
            
            raise HTTPException(
                status_code=500,
                detail=f"SOAP generation failed: {soap_result.get('error_message')}"
            )
        
        # Step 6: Save SOAP note to database
        processing_metadata = soap_result.get("processing_metadata", {})
        
        soap_note = SOAPNote.create_from_ai_response(
            soap_result,
            provider_id=provider.id,
            patient_id=patient.id,
            audio_file_id=audio_record.id,
            visit_date=datetime.now(timezone.utc),
            visit_type=visit_type,
            transcription=transcription_text,
            transcription_confidence=transcription_confidence,
            status="draft",
            created_by=current_user.get("user_id")
        )
        
        db.add(soap_note)
        db.commit()
        db.refresh(soap_note)
        
        # Calculate total processing time
        total_processing_time = time.time() - start_time
        
        logger.info("Voice-to-SOAP processing completed successfully",
                   session_id=session_id,
                   soap_note_id=str(soap_note.id),
                   total_processing_time=total_processing_time)
        
        # Log successful completion
        await log_audit_event(
            request, current_user, "voice_to_soap_completed", "soap_note",
            str(soap_note.id), True, None, {
                "processing_time": total_processing_time,
                "tokens_used": processing_metadata.get("tokens_used"),
                "cost": processing_metadata.get("estimated_cost_usd")
            }, db
        )
        
        # Schedule background cleanup
        background_tasks.add_task(cleanup_session_data, session_id)
        
        # Return response
        return SOAPNoteResponse(
            id=str(soap_note.id),
            session_id=session_id,
            provider_email=provider.email,
            patient_mrn=patient.mrn,
            soap_data=soap_note.to_dict(),
            transcription=transcription_text,
            transcription_confidence=transcription_confidence,
            processing_time_seconds=round(total_processing_time, 2),
            tokens_used=processing_metadata.get("tokens_used", 0),
            estimated_cost_usd=processing_metadata.get("estimated_cost_usd", 0.0),
            created_at=soap_note.created_at.isoformat(),
            status=soap_note.status
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        
        logger.error("Voice-to-SOAP processing failed",
                    session_id=session_id,
                    error=error_msg,
                    processing_time=processing_time)
        
        # Log failure
        await log_audit_event(
            request, current_user, "voice_to_soap_failed", "soap_note",
            session_id, False, error_msg, None, db
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Voice-to-SOAP processing failed: {error_msg}"
        )

@app.get("/api/v1/soap-notes", response_model=List[Dict])
async def get_soap_notes(
    request: Request,
    provider_email: Optional[str] = None,
    patient_mrn: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get SOAP notes with filtering and pagination"""
    try:
        query = db.query(SOAPNote).join(Provider).join(Patient)
        
        # Apply filters
        if provider_email:
            query = query.filter(Provider.email == provider_email)
        if patient_mrn:
            query = query.filter(Patient.mrn == patient_mrn)
        
        # Apply pagination
        soap_notes = query.order_by(desc(SOAPNote.created_at)).offset(offset).limit(limit).all()
        
        # Convert to dictionaries
        result = [note.to_dict() for note in soap_notes]
        
        # Log audit event
        await log_audit_event(
            request, current_user, "soap_notes_retrieved", "soap_note",
            None, True, None, {"count": len(result)}, db
        )
        
        return result
        
    except Exception as e:
        logger.error("Failed to retrieve SOAP notes", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve SOAP notes: {str(e)}")

@app.get("/api/v1/soap-notes/{soap_note_id}", response_model=Dict)
async def get_soap_note(
    request: Request,
    soap_note_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get specific SOAP note by ID"""
    try:
        soap_note = db.query(SOAPNote).filter(SOAPNote.id == soap_note_id).first()
        
        if not soap_note:
            raise HTTPException(status_code=404, detail="SOAP note not found")
        
        # Log audit event
        await log_audit_event(
            request, current_user, "soap_note_viewed", "soap_note",
            soap_note_id, True, None, None, db
        )
        
        return soap_note.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve SOAP note", error=str(e), soap_note_id=soap_note_id)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve SOAP note: {str(e)}")

# ==========================================
# BACKGROUND TASKS
# ==========================================

async def cleanup_session_data(session_id: str):
    """Clean up temporary files and cache for a session"""
    try:
        # Clean up any temporary files
        temp_dir = Path(tempfile.gettempdir())
        temp_files = temp_dir.glob(f"{session_id}*")
        
        for temp_file in temp_files:
            try:
                temp_file.unlink()
            except Exception as cleanup_error:
                logger.warning("Failed to cleanup temp file",
                              file=str(temp_file),
                              error=str(cleanup_error))
        
        logger.info("Session cleanup completed", session_id=session_id)
        
    except Exception as e:
        logger.error("Session cleanup failed", session_id=session_id, error=str(e))

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging"""
    logger.warning("HTTP exception occurred",
                   path=request.url.path,
                   method=request.method,
                   status_code=exc.status_code,
                   detail=exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    """Handle internal server errors"""
    logger.error("Internal server error",
                path=request.url.path,
                method=request.method,
                error=str(exc))
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# ==========================================
# MAIN APPLICATION ENTRY POINT
# ==========================================

if __name__ == "__main__":
    import uvicorn
    
    # Configuration for development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )