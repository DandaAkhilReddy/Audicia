"""
AUDICIA VOICE-TO-SOAP SYSTEM
OpenAI GPT-4 SOAP Note Generation Service
Medical documentation AI with clinical accuracy and HIPAA compliance
"""

import json
import time
from typing import Dict, Any, Optional, List
from openai import OpenAI
from simple_secret_manager import get_secret
import structlog

logger = structlog.get_logger()

class MedicalSOAPGenerator:
    """
    Production OpenAI GPT-4 service for generating medical SOAP notes
    Features:
    - Clinical accuracy optimization
    - Structured medical documentation
    - HIPAA-compliant processing
    - Cost tracking and optimization
    - Medical terminology validation
    """
    
    def __init__(self):
        """Initialize OpenAI client with medical optimization"""
        try:
            # Get OpenAI API key from Azure Key Vault
            api_key = get_secret("OPENAI_API_KEY")
            
            # Initialize OpenAI client
            self.client = OpenAI(api_key=api_key)
            
            # Configuration for medical documentation
            self.model = "gpt-4-turbo-preview"
            self.temperature = 0.1  # Low temperature for consistent medical documentation
            self.max_tokens = 3000
            self.timeout = 120  # 2 minutes timeout
            
            # Load medical prompts and templates
            self.system_prompt = self._create_medical_system_prompt()
            
            logger.info("OpenAI GPT-4 service initialized successfully",
                       model=self.model,
                       temperature=self.temperature)
            
        except Exception as e:
            logger.error("Failed to initialize OpenAI service", error=str(e))
            raise RuntimeError(f"OpenAI service initialization failed: {e}")
    
    def _create_medical_system_prompt(self) -> str:
        """Create comprehensive system prompt for medical SOAP generation"""
        return """
You are an expert medical AI assistant specializing in creating accurate, comprehensive SOAP notes from physician dictations. You must maintain complete medical accuracy and follow HIPAA-compliant documentation standards.

CRITICAL REQUIREMENTS:
1. ACCURACY: Maintain complete medical accuracy - never guess clinical information
2. COMPLETENESS: Extract all clinical information present in dictation  
3. STRUCTURE: Follow strict SOAP note formatting standards
4. COMPLIANCE: Ensure documentation meets healthcare regulatory standards
5. TERMINOLOGY: Use proper medical terminology and standard abbreviations

SOAP STRUCTURE REQUIREMENTS:

SUBJECTIVE:
- Chief Complaint: Primary reason for visit in patient's words (concise, under 10 words)
- History of Present Illness: Detailed chronological symptom description with timeline
- Review of Systems: Systematic review by body system (constitutional, cardiovascular, respiratory, etc.)
- Past Medical History: Previous conditions, surgeries, hospitalizations with dates
- Medications: Current medications with generic names, dosages, frequencies, and routes
- Allergies: Drug, food, and environmental allergies with reaction types and severity
- Social History: Smoking (pack-years), alcohol (drinks/week), drugs, occupation, living situation
- Family History: Relevant hereditary conditions with relationships and ages

OBJECTIVE:
- Vital Signs: BP (systolic/diastolic mmHg), HR (bpm), Temp (°F), RR (/min), SpO2 (%), Weight (lbs), Height (in), BMI
- Physical Examination: Systematic findings by body system using standard terminology
- Laboratory Results: Recent lab values with reference ranges and abnormal flags
- Imaging Results: Radiology findings with modality, date, and radiologist interpretation
- Diagnostic Tests: EKG findings, PFTs, other test results with normal/abnormal classification

ASSESSMENT:
- Primary Diagnosis: Most likely diagnosis with ICD-10 code (format: condition [ICD-10])
- Differential Diagnoses: Alternative diagnostic possibilities ranked by likelihood
- Clinical Impression: Medical reasoning, risk stratification, and clinical decision-making
- Problem List: Active medical problems prioritized by severity and management needs

PLAN:
- Medications: New prescriptions with drug name, strength, dosage, frequency, duration, quantity
- Procedures: Ordered interventions with indications and scheduling
- Laboratory Tests: Ordered lab work with timing and specific tests
- Imaging Studies: Ordered diagnostic imaging with modality, urgency, and indication
- Follow-up: Appointment scheduling, monitoring parameters, and return precautions
- Patient Education: Topics discussed, instructions given, and patient understanding
- Referrals: Specialist consultations with specialty, urgency, and indication

OUTPUT FORMAT:
Return ONLY valid JSON with this EXACT structure (no markdown, no explanations):

{
    "subjective": {
        "chief_complaint": "string (max 100 chars)",
        "history_present_illness": "string",
        "review_of_systems": "string", 
        "past_medical_history": "string",
        "medications": "string",
        "allergies": "string",
        "social_history": "string",
        "family_history": "string"
    },
    "objective": {
        "vital_signs": {
            "blood_pressure": "string",
            "heart_rate": "string",
            "temperature": "string", 
            "respiratory_rate": "string",
            "oxygen_saturation": "string",
            "weight": "string",
            "height": "string",
            "bmi": "string"
        },
        "physical_examination": "string",
        "laboratory_results": "string",
        "imaging_results": "string"
    },
    "assessment": {
        "primary_diagnosis": "string",
        "icd10_codes": ["string"],
        "differential_diagnoses": ["string"],
        "clinical_impression": "string"
    },
    "plan": {
        "medications": ["string"],
        "procedures": ["string"],
        "laboratory_tests": ["string"],
        "imaging_studies": ["string"],
        "follow_up": "string",
        "patient_education": "string", 
        "referrals": ["string"]
    },
    "metadata": {
        "confidence_score": 0.95,
        "completeness_score": 0.90,
        "medical_accuracy_score": 0.92,
        "missing_elements": ["string"]
    }
}

IMPORTANT RULES:
- Use "Not documented" for information not mentioned in the dictation
- Never fabricate medical information
- Include confidence scores based on information quality
- Use standard medical abbreviations appropriately
- Ensure all medications include generic names
- Include units for all measurements
- Flag any concerning findings in clinical impression
"""
    
    def generate_soap_note(self, 
                          transcription: str,
                          patient_context: Optional[Dict[str, Any]] = None,
                          provider_context: Optional[Dict[str, Any]] = None,
                          session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate structured SOAP note from medical transcription
        
        Args:
            transcription: Medical transcription text
            patient_context: Optional patient demographic information
            provider_context: Optional provider information
            session_id: Optional session ID for tracking
            
        Returns:
            Dict containing structured SOAP note and processing metadata
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not transcription or len(transcription.strip()) < 10:
                raise ValueError("Transcription too short or empty for medical documentation")
            
            logger.info("Starting SOAP note generation",
                       session_id=session_id,
                       transcription_length=len(transcription),
                       has_patient_context=bool(patient_context),
                       has_provider_context=bool(provider_context))
            
            # Create context-enhanced prompt
            enhanced_prompt = self._create_enhanced_prompt(
                transcription, patient_context, provider_context
            )
            
            # Call OpenAI GPT-4
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": enhanced_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            # Process the response
            soap_result = self._process_ai_response(
                response, transcription, session_id, start_time
            )
            
            logger.info("SOAP note generation completed successfully",
                       session_id=session_id,
                       processing_time=soap_result["processing_metadata"]["processing_time_seconds"],
                       tokens_used=soap_result["processing_metadata"]["tokens_used"])
            
            return soap_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_result = self._create_error_result(str(e), session_id, processing_time)
            
            logger.error("SOAP note generation failed",
                        session_id=session_id,
                        error=str(e),
                        processing_time=processing_time)
            
            return error_result
    
    def _create_enhanced_prompt(self, 
                               transcription: str,
                               patient_context: Optional[Dict[str, Any]],
                               provider_context: Optional[Dict[str, Any]]) -> str:
        """Create context-enhanced prompt for better AI processing"""
        
        prompt_parts = []
        
        # Add patient context if available
        if patient_context:
            context_info = []
            if patient_context.get("age"):
                context_info.append(f"Age: {patient_context['age']}")
            if patient_context.get("gender"):
                context_info.append(f"Gender: {patient_context['gender']}")
            if patient_context.get("known_conditions"):
                context_info.append(f"Known conditions: {', '.join(patient_context['known_conditions'])}")
            if patient_context.get("current_medications"):
                context_info.append(f"Current medications: {', '.join(patient_context['current_medications'])}")
            
            if context_info:
                prompt_parts.append(f"PATIENT CONTEXT:\n{chr(10).join(context_info)}")
        
        # Add provider context if available
        if provider_context:
            if provider_context.get("specialty"):
                prompt_parts.append(f"PROVIDER SPECIALTY: {provider_context['specialty']}")
        
        # Add the main transcription
        prompt_parts.append(f"MEDICAL DICTATION TO PROCESS:\n\"{transcription}\"")
        
        # Add processing instructions
        prompt_parts.append("""
Please create a comprehensive, clinically accurate SOAP note from this dictation. 
Use proper medical terminology and standard formatting. Return only valid JSON.
""")
        
        return "\n\n".join(prompt_parts)
    
    def _process_ai_response(self, 
                           response,
                           original_transcription: str,
                           session_id: Optional[str],
                           start_time: float) -> Dict[str, Any]:
        """Process OpenAI API response and validate SOAP note structure"""
        
        processing_time = time.time() - start_time
        
        try:
            # Extract response content
            response_content = response.choices[0].message.content
            usage_stats = response.usage
            
            # Parse JSON response
            try:
                soap_data = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON response from AI, attempting to fix",
                              session_id=session_id,
                              json_error=str(e))
                # Attempt to clean and re-parse
                soap_data = self._fix_json_response(response_content)
            
            # Validate SOAP structure
            validated_soap = self._validate_soap_structure(soap_data)
            
            # Enhance with quality metrics
            quality_metrics = self._assess_soap_quality(
                validated_soap, original_transcription
            )
            validated_soap["quality_metrics"] = quality_metrics
            
            # Add processing metadata
            validated_soap["processing_metadata"] = {
                "session_id": session_id,
                "model_used": self.model,
                "processing_time_seconds": round(processing_time, 2),
                "tokens_used": usage_stats.total_tokens,
                "prompt_tokens": usage_stats.prompt_tokens,
                "completion_tokens": usage_stats.completion_tokens,
                "estimated_cost_usd": self._calculate_cost(usage_stats),
                "transcription_length": len(original_transcription),
                "timestamp": time.time()
            }
            
            return validated_soap
            
        except Exception as e:
            logger.error("Failed to process AI response",
                        session_id=session_id,
                        error=str(e))
            raise RuntimeError(f"AI response processing failed: {e}")
    
    def _validate_soap_structure(self, soap_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and ensure SOAP note has required structure"""
        
        # Define required structure
        required_structure = {
            "subjective": {
                "chief_complaint": "",
                "history_present_illness": "",
                "review_of_systems": "",
                "past_medical_history": "",
                "medications": "",
                "allergies": "",
                "social_history": "",
                "family_history": ""
            },
            "objective": {
                "vital_signs": {
                    "blood_pressure": "",
                    "heart_rate": "",
                    "temperature": "",
                    "respiratory_rate": "",
                    "oxygen_saturation": "",
                    "weight": "",
                    "height": "",
                    "bmi": ""
                },
                "physical_examination": "",
                "laboratory_results": "",
                "imaging_results": ""
            },
            "assessment": {
                "primary_diagnosis": "",
                "icd10_codes": [],
                "differential_diagnoses": [],
                "clinical_impression": ""
            },
            "plan": {
                "medications": [],
                "procedures": [],
                "laboratory_tests": [],
                "imaging_studies": [],
                "follow_up": "",
                "patient_education": "",
                "referrals": []
            },
            "metadata": {
                "confidence_score": 0.5,
                "completeness_score": 0.5,
                "medical_accuracy_score": 0.5,
                "missing_elements": []
            }
        }
        
        # Merge provided data with required structure
        validated = self._merge_dict_structures(required_structure, soap_data)
        
        # Validate specific fields
        validated = self._validate_specific_fields(validated)
        
        return validated
    
    def _merge_dict_structures(self, template: Dict, data: Dict) -> Dict:
        """Recursively merge data into template structure"""
        result = template.copy()
        
        for key, value in data.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._merge_dict_structures(result[key], value)
                else:
                    result[key] = value
            # Allow additional fields not in template
            else:
                result[key] = value
        
        return result
    
    def _validate_specific_fields(self, soap_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean specific SOAP fields"""
        
        # Ensure arrays are actually arrays
        array_fields = [
            ("assessment", "icd10_codes"),
            ("assessment", "differential_diagnoses"), 
            ("plan", "medications"),
            ("plan", "procedures"),
            ("plan", "laboratory_tests"),
            ("plan", "imaging_studies"),
            ("plan", "referrals")
        ]
        
        for section, field in array_fields:
            if section in soap_data and field in soap_data[section]:
                value = soap_data[section][field]
                if not isinstance(value, list):
                    if isinstance(value, str) and value:
                        # Convert string to single-item list
                        soap_data[section][field] = [value]
                    else:
                        soap_data[section][field] = []
        
        # Validate confidence scores
        if "metadata" in soap_data:
            for score_field in ["confidence_score", "completeness_score", "medical_accuracy_score"]:
                if score_field in soap_data["metadata"]:
                    score = soap_data["metadata"][score_field]
                    if not isinstance(score, (int, float)) or score < 0 or score > 1:
                        soap_data["metadata"][score_field] = 0.5  # Default to 50%
        
        return soap_data
    
    def _assess_soap_quality(self, 
                           soap_data: Dict[str, Any],
                           original_transcription: str) -> Dict[str, Any]:
        """Assess the quality and completeness of generated SOAP note"""
        
        quality_metrics = {
            "completeness": self._assess_completeness(soap_data),
            "clinical_coherence": self._assess_clinical_coherence(soap_data),
            "transcription_fidelity": self._assess_transcription_fidelity(
                soap_data, original_transcription
            ),
            "medical_terminology": self._assess_medical_terminology(soap_data)
        }
        
        # Calculate overall quality score
        overall_score = sum(quality_metrics.values()) / len(quality_metrics)
        
        # Determine quality level
        if overall_score >= 0.8:
            quality_level = "excellent"
        elif overall_score >= 0.6:
            quality_level = "good"
        elif overall_score >= 0.4:
            quality_level = "fair"
        else:
            quality_level = "poor"
        
        return {
            "overall_score": round(overall_score, 2),
            "quality_level": quality_level,
            "detailed_metrics": quality_metrics,
            "recommendations": self._generate_quality_recommendations(quality_metrics)
        }
    
    def _assess_completeness(self, soap_data: Dict[str, Any]) -> float:
        """Assess completeness of SOAP note sections"""
        total_fields = 0
        completed_fields = 0
        
        # Check subjective section
        subjective_fields = soap_data.get("subjective", {})
        for field, value in subjective_fields.items():
            total_fields += 1
            if value and value != "Not documented":
                completed_fields += 1
        
        # Check objective section
        objective = soap_data.get("objective", {})
        vital_signs = objective.get("vital_signs", {})
        for field, value in vital_signs.items():
            total_fields += 1
            if value and value != "Not documented":
                completed_fields += 1
        
        for field in ["physical_examination", "laboratory_results", "imaging_results"]:
            total_fields += 1
            if objective.get(field) and objective.get(field) != "Not documented":
                completed_fields += 1
        
        # Check assessment section
        assessment = soap_data.get("assessment", {})
        for field in ["primary_diagnosis", "clinical_impression"]:
            total_fields += 1
            if assessment.get(field) and assessment.get(field) != "Not documented":
                completed_fields += 1
        
        # Check plan section
        plan = soap_data.get("plan", {})
        for field in ["follow_up", "patient_education"]:
            total_fields += 1
            if plan.get(field) and plan.get(field) != "Not documented":
                completed_fields += 1
        
        return completed_fields / total_fields if total_fields > 0 else 0
    
    def _assess_clinical_coherence(self, soap_data: Dict[str, Any]) -> float:
        """Assess clinical coherence between SOAP sections"""
        # This is a simplified assessment - in production, would use more sophisticated NLP
        coherence_score = 0.5  # Default neutral score
        
        # Check if assessment aligns with subjective symptoms
        subjective = soap_data.get("subjective", {})
        assessment = soap_data.get("assessment", {})
        
        chief_complaint = subjective.get("chief_complaint", "").lower()
        primary_diagnosis = assessment.get("primary_diagnosis", "").lower()
        
        # Simple keyword matching for coherence
        if chief_complaint and primary_diagnosis:
            # Extract key symptoms from chief complaint
            symptom_keywords = ["pain", "fever", "cough", "nausea", "headache"]
            found_symptoms = [kw for kw in symptom_keywords if kw in chief_complaint]
            
            if found_symptoms:
                # Check if diagnosis relates to symptoms
                if any(symptom in primary_diagnosis for symptom in found_symptoms):
                    coherence_score = 0.8
        
        return coherence_score
    
    def _assess_transcription_fidelity(self, 
                                     soap_data: Dict[str, Any],
                                     original_transcription: str) -> float:
        """Assess how well SOAP note reflects original transcription"""
        # Extract key information from transcription
        transcription_lower = original_transcription.lower()
        
        # Check if key transcribed information appears in SOAP note
        soap_text = json.dumps(soap_data).lower()
        
        # Simple word overlap assessment
        transcription_words = set(transcription_lower.split())
        soap_words = set(soap_text.split())
        
        # Remove common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were"}
        transcription_words -= common_words
        soap_words -= common_words
        
        if transcription_words:
            overlap = len(transcription_words & soap_words) / len(transcription_words)
            return min(overlap, 1.0)
        
        return 0.5  # Default if no meaningful words to compare
    
    def _assess_medical_terminology(self, soap_data: Dict[str, Any]) -> float:
        """Assess appropriate use of medical terminology"""
        soap_text = json.dumps(soap_data).lower()
        
        # Count medical terms
        medical_terms = [
            "diagnosis", "treatment", "medication", "examination", "assessment",
            "chronic", "acute", "bilateral", "unilateral", "anterior", "posterior",
            "cardiovascular", "respiratory", "neurological", "gastrointestinal"
        ]
        
        found_terms = sum(1 for term in medical_terms if term in soap_text)
        terminology_score = min(found_terms / 10, 1.0)  # Normalize to max 10 terms
        
        return terminology_score
    
    def _generate_quality_recommendations(self, quality_metrics: Dict[str, float]) -> List[str]:
        """Generate recommendations for improving SOAP note quality"""
        recommendations = []
        
        if quality_metrics["completeness"] < 0.6:
            recommendations.append("Include more complete patient history and examination findings")
        
        if quality_metrics["clinical_coherence"] < 0.6:
            recommendations.append("Ensure assessment aligns with subjective complaints and objective findings")
        
        if quality_metrics["transcription_fidelity"] < 0.6:
            recommendations.append("Transcription may need clarification - consider re-recording")
        
        if quality_metrics["medical_terminology"] < 0.5:
            recommendations.append("Consider using more specific medical terminology")
        
        if not recommendations:
            recommendations.append("Excellent SOAP note quality - meets clinical documentation standards")
        
        return recommendations
    
    def _fix_json_response(self, response_content: str) -> Dict[str, Any]:
        """Attempt to fix malformed JSON response"""
        try:
            # Remove potential markdown formatting
            cleaned = response_content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            # Try parsing again
            return json.loads(cleaned)
            
        except json.JSONDecodeError:
            # Return minimal valid structure if all else fails
            logger.warning("Could not fix malformed JSON, returning minimal structure")
            return {
                "subjective": {"chief_complaint": "Parse error - please review transcription"},
                "objective": {"vital_signs": {}, "physical_examination": "Parse error"},
                "assessment": {"primary_diagnosis": "Unable to process", "icd10_codes": []},
                "plan": {"medications": [], "follow_up": "Review needed"},
                "metadata": {"confidence_score": 0.1, "completeness_score": 0.1}
            }
    
    def _calculate_cost(self, usage_stats) -> float:
        """Calculate estimated API cost for the request"""
        # GPT-4 pricing (as of 2024) - adjust as needed
        prompt_cost_per_token = 0.00003  # $0.03 per 1K tokens
        completion_cost_per_token = 0.00006  # $0.06 per 1K tokens
        
        prompt_cost = usage_stats.prompt_tokens * prompt_cost_per_token
        completion_cost = usage_stats.completion_tokens * completion_cost_per_token
        
        return round(prompt_cost + completion_cost, 4)
    
    def _create_error_result(self, 
                           error_message: str,
                           session_id: Optional[str],
                           processing_time: float) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            "success": False,
            "error_message": error_message,
            "processing_metadata": {
                "session_id": session_id,
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": time.time()
            }
        }

# Global SOAP generator instance
soap_generator = MedicalSOAPGenerator()

# Convenience functions
def generate_soap(transcription: str,
                 patient_context: Optional[Dict[str, Any]] = None,
                 provider_context: Optional[Dict[str, Any]] = None,
                 session_id: Optional[str] = None) -> Dict[str, Any]:
    """Generate SOAP note from transcription - main entry point"""
    return soap_generator.generate_soap_note(
        transcription, patient_context, provider_context, session_id
    )

if __name__ == "__main__":
    # Test SOAP generator
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("Testing OpenAI SOAP generation service...")
        
        # Test initialization
        test_generator = MedicalSOAPGenerator()
        print("✅ OpenAI service initialized successfully!")
        
        # Test with sample transcription
        sample_transcription = """
        Patient is a 45-year-old male presenting with chest pain that started 2 hours ago.
        Pain is described as pressure-like, substernal, radiating to left arm.
        Associated with mild shortness of breath and diaphoresis.
        Vital signs: blood pressure 140 over 90, heart rate 88, temperature 98.4.
        Physical exam shows regular rate and rhythm, no murmurs.
        """
        
        print("Testing SOAP generation with sample transcription...")
        result = test_generator.generate_soap_note(sample_transcription, session_id="test-001")
        
        if result.get("success", True):  # Default True for backward compatibility
            print("✅ SOAP note generated successfully!")
            print(f"Primary diagnosis: {result.get('assessment', {}).get('primary_diagnosis', 'N/A')}")
        else:
            print(f"❌ SOAP generation failed: {result.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ SOAP generator test failed: {e}")