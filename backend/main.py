"""
Audicia SOAP Note System - Enterprise Backend API
FastAPI-based microservices for medical documentation
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import hashlib
import jwt
import os
from contextlib import asynccontextmanager

# Environment configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
AZURE_STORAGE_CONNECTION = os.getenv("AZURE_STORAGE_CONNECTION", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/audicia")

# Initialize FastAPI app
app = FastAPI(
    title="Audicia SOAP Note API",
    description="Enterprise Medical Documentation System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://audicia.yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ==================== MODELS ====================

class UserRole(str, Enum):
    PHYSICIAN = "physician"
    NURSE = "nurse"
    ADMIN = "admin"
    RESIDENT = "resident"
    MEDICAL_STUDENT = "medical_student"

class VitalSigns(BaseModel):
    blood_pressure_systolic: Optional[int] = Field(None, ge=0, le=300)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=0, le=200)
    heart_rate: Optional[int] = Field(None, ge=0, le=300)
    temperature: Optional[float] = Field(None, ge=90, le=110)
    respiratory_rate: Optional[int] = Field(None, ge=0, le=100)
    oxygen_saturation: Optional[int] = Field(None, ge=0, le=100)
    weight: Optional[float] = Field(None, ge=0)
    height: Optional[float] = Field(None, ge=0)
    bmi: Optional[float] = Field(None, ge=0)

class SubjectiveSection(BaseModel):
    chief_complaint: str = Field(..., min_length=1, max_length=500)
    history_present_illness: str = Field(..., min_length=1, max_length=5000)
    review_of_systems: Optional[str] = Field(None, max_length=3000)
    past_medical_history: Optional[str] = Field(None, max_length=3000)
    medications: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    social_history: Optional[str] = Field(None, max_length=2000)
    family_history: Optional[str] = Field(None, max_length=2000)

class ObjectiveSection(BaseModel):
    vital_signs: VitalSigns
    physical_examination: str = Field(..., min_length=1, max_length=5000)
    laboratory_results: Optional[str] = Field(None, max_length=3000)
    imaging_results: Optional[str] = Field(None, max_length=3000)

class AssessmentSection(BaseModel):
    primary_diagnosis: str = Field(..., min_length=1, max_length=500)
    secondary_diagnoses: Optional[List[str]] = []
    differential_diagnoses: Optional[List[str]] = []
    clinical_impression: Optional[str] = Field(None, max_length=3000)

class PlanSection(BaseModel):
    medications: Optional[List[Dict[str, str]]] = []
    procedures: Optional[List[str]] = []
    laboratory_tests: Optional[List[str]] = []
    imaging_studies: Optional[List[str]] = []
    follow_up: Optional[str] = Field(None, max_length=500)
    patient_education: Optional[str] = Field(None, max_length=2000)
    referrals: Optional[List[str]] = []

class SOAPNote(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    patient_name: str
    patient_dob: str
    mrn: str
    encounter_date: datetime = Field(default_factory=datetime.now)
    provider_id: str
    provider_name: str
    subjective: SubjectiveSection
    objective: ObjectiveSection
    assessment: AssessmentSection
    plan: PlanSection
    status: str = "draft"  # draft, final, amended
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    signed_at: Optional[datetime] = None
    version: int = 1
    tags: Optional[List[str]] = []
    
class PatientInfo(BaseModel):
    patient_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_id: Optional[str] = None
    emergency_contact: Optional[str] = None
    primary_physician: Optional[str] = None

class User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    full_name: str
    role: UserRole
    license_number: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

class Token(BaseModel):
    access_token: str
    token_type: str

# ==================== DATABASE (Mock) ====================

# In production, this would be replaced with actual database connections
soap_notes_db: Dict[str, SOAPNote] = {}
patients_db: Dict[str, PatientInfo] = {}
users_db: Dict[str, User] = {}
templates_db: Dict[str, Dict] = {}

# ==================== AUTHENTICATION ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # In production, fetch from database
    user = users_db.get(username)
    if user is None:
        raise credentials_exception
    return user

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "message": "Audicia SOAP Note System API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/api/docs"
    }

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT token"""
    # In production, verify against database with hashed passwords
    # This is a mock implementation
    if form_data.username == "demo" and form_data.password == "demo123":
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.post("/api/soap-notes", response_model=SOAPNote)
async def create_soap_note(
    soap_note: SOAPNote,
    current_user: User = Depends(get_current_user)
):
    """Create a new SOAP note"""
    soap_note.provider_id = current_user.user_id
    soap_note.provider_name = current_user.full_name
    soap_note.created_at = datetime.now()
    soap_note.updated_at = datetime.now()
    
    # Store in database (mock)
    soap_notes_db[soap_note.id] = soap_note
    
    return soap_note

@app.get("/api/soap-notes", response_model=List[SOAPNote])
async def get_soap_notes(
    patient_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Retrieve SOAP notes with optional filters"""
    notes = list(soap_notes_db.values())
    
    # Apply filters
    if patient_id:
        notes = [n for n in notes if n.patient_id == patient_id]
    if provider_id:
        notes = [n for n in notes if n.provider_id == provider_id]
    if status:
        notes = [n for n in notes if n.status == status]
    
    # Sort by created date (newest first)
    notes.sort(key=lambda x: x.created_at, reverse=True)
    
    return notes[:limit]

@app.get("/api/soap-notes/{note_id}", response_model=SOAPNote)
async def get_soap_note(
    note_id: str,
    current_user: User = Depends(get_current_user)
):
    """Retrieve a specific SOAP note by ID"""
    note = soap_notes_db.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="SOAP note not found")
    return note

@app.put("/api/soap-notes/{note_id}", response_model=SOAPNote)
async def update_soap_note(
    note_id: str,
    soap_note: SOAPNote,
    current_user: User = Depends(get_current_user)
):
    """Update an existing SOAP note"""
    if note_id not in soap_notes_db:
        raise HTTPException(status_code=404, detail="SOAP note not found")
    
    existing_note = soap_notes_db[note_id]
    
    # Check if user has permission to edit
    if existing_note.provider_id != current_user.user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to edit this note")
    
    # Update fields
    soap_note.id = note_id
    soap_note.updated_at = datetime.now()
    soap_note.version = existing_note.version + 1
    
    soap_notes_db[note_id] = soap_note
    return soap_note

@app.post("/api/soap-notes/{note_id}/sign")
async def sign_soap_note(
    note_id: str,
    current_user: User = Depends(get_current_user)
):
    """Electronically sign a SOAP note"""
    if note_id not in soap_notes_db:
        raise HTTPException(status_code=404, detail="SOAP note not found")
    
    note = soap_notes_db[note_id]
    
    # Check if user is the provider
    if note.provider_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only the provider can sign this note")
    
    note.status = "final"
    note.signed_at = datetime.now()
    
    return {"message": "SOAP note signed successfully", "signed_at": note.signed_at}

@app.delete("/api/soap-notes/{note_id}")
async def delete_soap_note(
    note_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a SOAP note (soft delete in production)"""
    if note_id not in soap_notes_db:
        raise HTTPException(status_code=404, detail="SOAP note not found")
    
    note = soap_notes_db[note_id]
    
    # Check permissions
    if note.provider_id != current_user.user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this note")
    
    # Check if note is signed
    if note.status == "final":
        raise HTTPException(status_code=400, detail="Cannot delete signed notes")
    
    del soap_notes_db[note_id]
    return {"message": "SOAP note deleted successfully"}

@app.get("/api/patients", response_model=List[PatientInfo])
async def get_patients(
    search: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Search and retrieve patient information"""
    patients = list(patients_db.values())
    
    if search:
        search_lower = search.lower()
        patients = [
            p for p in patients
            if search_lower in p.first_name.lower() or
               search_lower in p.last_name.lower() or
               search_lower in p.mrn.lower()
        ]
    
    return patients[:limit]

@app.post("/api/patients", response_model=PatientInfo)
async def create_patient(
    patient: PatientInfo,
    current_user: User = Depends(get_current_user)
):
    """Register a new patient"""
    # Check if MRN already exists
    if any(p.mrn == patient.mrn for p in patients_db.values()):
        raise HTTPException(status_code=400, detail="MRN already exists")
    
    patients_db[patient.patient_id] = patient
    return patient

@app.get("/api/templates")
async def get_templates(
    specialty: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Retrieve SOAP note templates"""
    templates = [
        {
            "id": "1",
            "name": "General Follow-up",
            "specialty": "General",
            "description": "Standard follow-up visit template"
        },
        {
            "id": "2",
            "name": "New Patient Intake",
            "specialty": "General",
            "description": "Comprehensive new patient evaluation"
        },
        {
            "id": "3",
            "name": "Emergency Visit",
            "specialty": "Emergency",
            "description": "Emergency department visit template"
        },
        {
            "id": "4",
            "name": "Pediatric Well-Child",
            "specialty": "Pediatrics",
            "description": "Routine pediatric check-up"
        }
    ]
    
    if specialty:
        templates = [t for t in templates if t["specialty"] == specialty]
    
    return templates

@app.post("/api/soap-notes/voice-to-text")
async def voice_to_text(
    audio_file: bytes,
    current_user: User = Depends(get_current_user)
):
    """Convert voice recording to text (Azure Cognitive Services integration)"""
    # In production, integrate with Azure Cognitive Services
    # This is a mock response
    return {
        "transcription": "Patient presents with chief complaint of headache for three days...",
        "confidence": 0.95,
        "duration": 45.2
    }

@app.get("/api/suggestions/diagnoses")
async def get_diagnosis_suggestions(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """Get ICD-10 diagnosis code suggestions"""
    # Mock ICD-10 suggestions
    suggestions = [
        {"code": "R51", "description": "Headache"},
        {"code": "G43.909", "description": "Migraine, unspecified"},
        {"code": "G44.1", "description": "Tension-type headache"},
    ]
    
    return suggestions

@app.get("/api/suggestions/medications")
async def get_medication_suggestions(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """Get medication suggestions with dosing"""
    # Mock medication suggestions
    suggestions = [
        {
            "name": "Ibuprofen",
            "dosage": "400-800mg",
            "frequency": "every 6-8 hours",
            "route": "PO"
        },
        {
            "name": "Sumatriptan",
            "dosage": "50-100mg",
            "frequency": "as needed",
            "route": "PO"
        }
    ]
    
    return suggestions

@app.get("/api/analytics/dashboard")
async def get_analytics_dashboard(
    current_user: User = Depends(get_current_user)
):
    """Get analytics dashboard data"""
    return {
        "total_notes": len(soap_notes_db),
        "notes_today": 12,
        "notes_this_week": 67,
        "notes_this_month": 245,
        "average_completion_time": "8.5 minutes",
        "most_common_diagnoses": [
            {"diagnosis": "Hypertension", "count": 45},
            {"diagnosis": "Type 2 Diabetes", "count": 38},
            {"diagnosis": "Upper Respiratory Infection", "count": 32}
        ],
        "provider_stats": {
            "notes_created": 89,
            "average_daily": 4.5,
            "completion_rate": 0.96
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "dependencies": {
            "database": "connected",
            "azure_storage": "connected",
            "redis_cache": "connected"
        }
    }

# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Initialize connections and load configurations"""
    print("Audicia SOAP Note System - Starting up...")
    # Initialize database connections
    # Load configurations
    # Set up Azure connections
    
    # Create demo data
    demo_user = User(
        user_id="demo-user-1",
        username="demo",
        email="demo@audicia.com",
        full_name="Dr. Demo User",
        role=UserRole.PHYSICIAN,
        license_number="MD123456",
        department="Internal Medicine"
    )
    users_db["demo"] = demo_user
    
    print("System ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections and resources"""
    print("Audicia SOAP Note System - Shutting down...")
    # Close database connections
    # Clean up resources
    print("Shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )