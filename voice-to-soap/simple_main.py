"""
AUDICIA VOICE-TO-SOAP SYSTEM
Simplified Production Server for Quick Testing
"""

import os
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.append(str(backend_path))

# Now import our modules
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import uuid

# Import our services
from simple_secret_manager import validate_production_secrets, get_secret
from transcriber import transcribe_audio_bytes
from soap_generator import generate_soap

# Create FastAPI app
app = FastAPI(
    title="Audicia Voice-to-SOAP API",
    description="HIPAA-Compliant Medical Documentation",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Audicia Voice-to-SOAP API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test secrets
        secrets_valid = validate_production_secrets()
        
        # Test basic services
        db_host = get_secret("PG_HOST")
        speech_key_available = bool(get_secret("AZURE_SPEECH_KEY"))
        openai_key_available = bool(get_secret("OPENAI_API_KEY"))
        
        return {
            "status": "healthy" if secrets_valid else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "secrets": "healthy" if secrets_valid else "unhealthy",
                "database_config": "configured" if db_host else "missing",
                "azure_speech": "configured" if speech_key_available else "missing",
                "openai": "configured" if openai_key_available else "missing"
            },
            "configuration": {
                "database_host": db_host,
                "speech_region": get_secret("AZURE_SPEECH_REGION")
            }
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@app.post("/api/v1/voice-to-soap-simple")
async def voice_to_soap_simple(
    audio_file: UploadFile = File(...),
    doctor_email: str = Form(...),
    patient_mrn: str = Form(...)
):
    """
    Simplified voice-to-SOAP endpoint for testing
    """
    session_id = str(uuid.uuid4())
    
    try:
        print(f"Processing voice-to-SOAP request: {session_id}")
        
        # Read audio data
        audio_data = await audio_file.read()
        print(f"Audio file received: {len(audio_data)} bytes")
        
        # Mock transcription for now (since we need actual audio file)
        mock_transcription = {
            "success": True,
            "transcription": "Patient is a 45-year-old male presenting with chest pain that started 2 hours ago. Pain is described as pressure-like, substernal, radiating to left arm. Vital signs show blood pressure 140 over 90, heart rate 88, temperature 98.4 degrees Fahrenheit. Physical examination reveals regular rate and rhythm, no murmurs.",
            "confidence_score": "high",
            "processing_time_seconds": 8.5,
            "medical_terms_detected": 8
        }
        
        print("Using mock transcription for testing")
        
        # Generate SOAP note with OpenAI
        print("Generating SOAP note with OpenAI...")
        soap_result = generate_soap(
            mock_transcription["transcription"], 
            session_id=session_id
        )
        
        # Return complete response
        result = {
            "success": True,
            "session_id": session_id,
            "provider_email": doctor_email,
            "patient_mrn": patient_mrn,
            "transcription": mock_transcription["transcription"],
            "transcription_confidence": mock_transcription["confidence_score"],
            "soap_data": soap_result,
            "processing_time_seconds": mock_transcription["processing_time_seconds"],
            "tokens_used": soap_result.get("processing_metadata", {}).get("tokens_used", 0),
            "estimated_cost_usd": soap_result.get("processing_metadata", {}).get("estimated_cost_usd", 0.0),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed"
        }
        
        print(f"Voice-to-SOAP completed successfully: {session_id}")
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"Voice-to-SOAP failed: {error_msg}")
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_msg,
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

# Test endpoint to verify OpenAI connection
@app.post("/api/v1/test-soap-generation")
async def test_soap_generation():
    """Test SOAP generation with sample transcription"""
    try:
        sample_transcription = "Patient is a 65-year-old female presenting with shortness of breath and chest tightness for 3 hours. Associated with nausea. Vital signs: BP 150/95, HR 92, Temp 98.2, RR 20, SpO2 94%."
        
        soap_result = generate_soap(sample_transcription, session_id="test-001")
        
        return {
            "success": True,
            "sample_transcription": sample_transcription,
            "soap_result": soap_result
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)