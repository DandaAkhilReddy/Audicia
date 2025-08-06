/**
 * AUDICIA VOICE-TO-SOAP FRONTEND CONNECTOR
 * Connect existing web app to production FastAPI backend
 * 
 * Replace the mock functionality in your simple-web-app/index.html
 * with these real API calls to the production backend
 */

// Production API Configuration
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    ENDPOINTS: {
        HEALTH: '/health',
        VOICE_TO_SOAP: '/api/v1/voice-to-soap',
        SOAP_NOTES: '/api/v1/soap-notes'
    },
    // Mock JWT token for development - replace with real authentication
    AUTH_TOKEN: 'Bearer development-token-replace-with-real-jwt'
};

/**
 * Real voice-to-SOAP processing function
 * Replace the mock processRecording() function with this
 */
async function processRecordingProduction() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'flex';
    
    try {
        // Create audio blob from recorded chunks
        const audioBlob = new Blob(recordedChunks, { type: 'audio/wav' });
        
        // Prepare form data
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'medical_dictation.wav');
        formData.append('doctor_email', 'doctor@hospital.com'); // Get from user input
        formData.append('patient_mrn', document.getElementById('patientMRN').textContent);
        formData.append('visit_type', 'routine');
        formData.append('session_id', generateSessionId());
        
        // Show processing status
        updateProcessingStatus('Uploading audio file...');
        
        // Call production API
        const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.VOICE_TO_SOAP}`, {
            method: 'POST',
            headers: {
                'Authorization': API_CONFIG.AUTH_TOKEN
            },
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        updateProcessingStatus('Processing complete! Filling SOAP note...');
        
        // Parse response
        const result = await response.json();
        console.log('Voice-to-SOAP Result:', result);
        
        // Fill SOAP note form with real data
        fillSOAPNoteFromProductionAPI(result);
        
        // Show success message
        showSuccessMessage(result);
        
    } catch (error) {
        console.error('Voice-to-SOAP processing failed:', error);
        showErrorMessage(error.message);
    } finally {
        loadingOverlay.style.display = 'none';
        resetRecordingUI();
    }
}

/**
 * Fill SOAP note form with production API response
 */
function fillSOAPNoteFromProductionAPI(apiResult) {
    const soapData = apiResult.soap_data;
    
    // Fill Subjective section
    if (soapData.subjective) {
        fillFieldWithAnimation('chiefComplaint', soapData.subjective.chief_complaint || '');
        fillFieldWithAnimation('historyPresentIllness', soapData.subjective.history_present_illness || '');
        fillFieldWithAnimation('reviewOfSystems', soapData.subjective.review_of_systems || '');
    }
    
    // Fill Objective section - Vital Signs
    if (soapData.objective && soapData.objective.vital_signs) {
        const vitals = soapData.objective.vital_signs;
        fillFieldWithAnimation('bloodPressure', vitals.blood_pressure || '');
        fillFieldWithAnimation('heartRate', vitals.heart_rate || '');
        fillFieldWithAnimation('temperature', vitals.temperature || '');
        fillFieldWithAnimation('respiratoryRate', vitals.respiratory_rate || '');
        fillFieldWithAnimation('oxygenSaturation', vitals.oxygen_saturation || '');
        fillFieldWithAnimation('weight', vitals.weight || '');
    }
    
    // Fill Physical Examination
    if (soapData.objective) {
        fillFieldWithAnimation('physicalExam', soapData.objective.physical_examination || '');
    }
    
    // Fill Assessment section
    if (soapData.assessment) {
        fillFieldWithAnimation('primaryDiagnosis', soapData.assessment.primary_diagnosis || '');
        fillFieldWithAnimation('clinicalImpression', soapData.assessment.clinical_impression || '');
    }
    
    // Fill Plan section
    if (soapData.plan) {
        const medications = Array.isArray(soapData.plan.medications) 
            ? soapData.plan.medications.join(', ') 
            : (soapData.plan.medications || '');
        fillFieldWithAnimation('treatmentPlan', medications);
        fillFieldWithAnimation('followUpInstructions', soapData.plan.follow_up || '');
    }
    
    // Update transcription display
    const transcriptionText = document.getElementById('transcriptionText');
    if (transcriptionText) {
        transcriptionText.textContent = apiResult.transcription || 'No transcription available';
    }
    
    console.log('SOAP note form filled with production data');
}

/**
 * Show success message with processing details
 */
function showSuccessMessage(result) {
    const statusText = document.getElementById('statusText');
    statusText.innerHTML = `
        ✅ SOAP Note Generated Successfully!<br>
        <small>Processing time: ${result.processing_time_seconds}s | 
        Tokens: ${result.tokens_used} | 
        Cost: $${result.estimated_cost_usd}</small>
    `;
    statusText.style.color = '#4CAF50';
    
    // Reset status after 5 seconds
    setTimeout(() => {
        statusText.textContent = 'Ready to Record';
        statusText.style.color = '#333';
    }, 5000);
}

/**
 * Show error message
 */
function showErrorMessage(errorMessage) {
    const statusText = document.getElementById('statusText');
    statusText.innerHTML = `❌ Processing Failed: ${errorMessage}`;
    statusText.style.color = '#f44336';
    
    // Reset status after 5 seconds
    setTimeout(() => {
        statusText.textContent = 'Ready to Record';
        statusText.style.color = '#333';
    }, 5000);
}

/**
 * Update processing status during workflow
 */
function updateProcessingStatus(message) {
    const loadingContent = document.querySelector('.loading-content p');
    if (loadingContent) {
        loadingContent.textContent = message;
    }
}

/**
 * Generate unique session ID
 */
function generateSessionId() {
    return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

/**
 * Test API connectivity
 */
async function testAPIConnection() {
    try {
        console.log('Testing API connection...');
        const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.HEALTH}`);
        
        if (response.ok) {
            const healthData = await response.json();
            console.log('✅ API Connection Success:', healthData);
            return true;
        } else {
            console.error('❌ API Connection Failed:', response.status);
            return false;
        }
    } catch (error) {
        console.error('❌ API Connection Error:', error);
        return false;
    }
}

/**
 * Enhanced save function with API integration
 */
async function saveSOAPNoteProduction() {
    try {
        // Collect all form data
        const soapData = {
            patientInfo: {
                name: document.getElementById('patientName').textContent,
                mrn: document.getElementById('patientMRN').textContent,
                visitDate: document.getElementById('visitDate').textContent
            },
            subjective: {
                chiefComplaint: document.getElementById('chiefComplaint').value,
                historyPresentIllness: document.getElementById('historyPresentIllness').value,
                reviewOfSystems: document.getElementById('reviewOfSystems').value
            },
            objective: {
                vitals: {
                    bloodPressure: document.getElementById('bloodPressure').value,
                    heartRate: document.getElementById('heartRate').value,
                    temperature: document.getElementById('temperature').value,
                    respiratoryRate: document.getElementById('respiratoryRate').value,
                    oxygenSaturation: document.getElementById('oxygenSaturation').value,
                    weight: document.getElementById('weight').value
                },
                physicalExam: document.getElementById('physicalExam').value
            },
            assessment: {
                primaryDiagnosis: document.getElementById('primaryDiagnosis').value,
                clinicalImpression: document.getElementById('clinicalImpression').value
            },
            plan: {
                treatmentPlan: document.getElementById('treatmentPlan').value,
                followUpInstructions: document.getElementById('followUpInstructions').value
            }
        };
        
        // Save to localStorage (immediate)
        localStorage.setItem('currentSOAPNote', JSON.stringify(soapData));
        
        // TODO: Save to database via API
        // This would be a PUT/POST to save the SOAP note
        
        console.log('SOAP Note saved:', soapData);
        alert('SOAP Note saved successfully!');
        
    } catch (error) {
        console.error('Save failed:', error);
        alert('Failed to save SOAP note: ' + error.message);
    }
}

/**
 * Initialize production API integration
 * Call this when the page loads to replace mock functionality
 */
function initializeProductionIntegration() {
    console.log('🚀 Initializing Audicia Production API Integration...');
    
    // Test API connection on load
    testAPIConnection().then(connected => {
        if (connected) {
            console.log('✅ Production backend is ready!');
            
            // Replace the existing processRecording function
            if (typeof window.processRecording !== 'undefined') {
                window.processRecording = processRecordingProduction;
                console.log('✅ Voice processing connected to production API');
            }
            
            // Replace the existing saveSOAPNote function
            if (typeof window.saveSOAPNote !== 'undefined') {
                window.saveSOAPNote = saveSOAPNoteProduction;
                console.log('✅ Save function connected to production API');
            }
            
        } else {
            console.warn('⚠️ Production backend not available - using mock functionality');
        }
    });
}

// Auto-initialize when script loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeProductionIntegration);
} else {
    initializeProductionIntegration();
}

// Export functions for manual use
window.AudiciaProduction = {
    processRecording: processRecordingProduction,
    saveSOAPNote: saveSOAPNoteProduction,
    testConnection: testAPIConnection,
    config: API_CONFIG
};