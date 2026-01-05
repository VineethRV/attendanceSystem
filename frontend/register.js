/**
 * Registration page logic
 * Handles student registration with face capture
 */

let capturedEmbeddings = [];
let captureCount = 0;
let isCapturing = false;

// DOM Elements
const registrationFormSection = document.getElementById('registration-form-section');
const cameraSection = document.getElementById('camera-section');
const successSection = document.getElementById('success-section');

const registrationForm = document.getElementById('registration-form');
const studentNameInput = document.getElementById('student-name');
const studentUsnInput = document.getElementById('student-usn');
const registrationKeyInput = document.getElementById('registration-key');
const studentSemesterSelect = document.getElementById('student-semester');
const studentSectionSelect = document.getElementById('student-section');

const webcam = document.getElementById('webcam');
const overlay = document.getElementById('overlay');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const captureBtn = document.getElementById('capture-btn');
const cancelCameraBtn = document.getElementById('cancel-camera-btn');

const successMessage = document.getElementById('success-message');

// Student data
let studentData = {};

/**
 * Initialize registration page
 */
async function init() {
    console.log('🚀 Initializing Registration Page...');
    
    // Load TensorFlow models
    try {
        showMessage('Loading face recognition models...', false);
        await loadModels();
        console.log('✅ Models loaded successfully');
        hideMessage();
    } catch (error) {
        console.error('Model loading failed:', error);
        showMessage('Warning: Face recognition models may not work properly', true);
    }
    
    // Check if already registered
    const existingStudent = getStudentData();
    if (existingStudent && existingStudent.usn) {
        showMessage(`You are already registered as ${existingStudent.name}. You can update your registration below.`, false);
        // Pre-fill form (except key)
        studentNameInput.value = existingStudent.name || '';
        studentUsnInput.value = existingStudent.usn || '';
        studentSemesterSelect.value = existingStudent.semester || '';
        studentSectionSelect.value = existingStudent.section || '';
    }
    
    // Set up event listeners
    setupEventListeners();
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    registrationForm.addEventListener('submit', handleFormSubmit);
    cancelCameraBtn.addEventListener('click', cancelCamera);
}

/**
 * Handle form submission - validate key first
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    
    // Validate form
    const name = studentNameInput.value.trim();
    const usn = studentUsnInput.value.trim().toUpperCase();
    const registrationKey = registrationKeyInput.value.trim().toUpperCase();
    const semester = studentSemesterSelect.value;
    const section = studentSectionSelect.value;
    
    if (!name || !usn || !registrationKey || !semester || !section) {
        showMessage('Please fill in all fields including the registration key', true);
        return;
    }
    
    // Validate USN format
    if (!/^1RV23CS\d{3}$/.test(usn)) {
        showMessage('Invalid USN format. Use: 1RV23CS001 to 1RV23CS450', true);
        return;
    }
    
    // Validate registration key with backend
    showMessage('🔑 Validating registration key...', false);
    
    try {
        const response = await apiCall('/api/validate-key', 'POST', {
            student_id: usn,
            registration_key: registrationKey
        });
        
        if (!response.valid) {
            showMessage(`❌ ${response.message}`, true);
            return;
        }
        
        showMessage('✅ Key validated! Starting face capture...', false);
        
    } catch (error) {
        showMessage(`❌ Key validation failed: ${error.message}`, true);
        return;
    }
    
    // Store student data temporarily (including key for registration)
    studentData = {
        name: name,
        usn: usn,
        registrationKey: registrationKey,
        semester: semester,
        section: section
    };
    
    // Proceed to camera capture
    showSection('camera');
    capturedEmbeddings = [];
    captureCount = 0;
    updateProgress();
    
    try {
        await startWebcam(webcam);
        
        // Sync overlay with video
        webcam.addEventListener('loadedmetadata', () => {
            overlay.width = webcam.videoWidth;
            overlay.height = webcam.videoHeight;
        });
        
        // Start automatic capture
        startAutomaticCapture();
        
    } catch (error) {
        showMessage(error.message, true);
        showSection('form');
    }
}

/**
 * Show specific section
 */
function showSection(section) {
    registrationFormSection.classList.add('hidden');
    cameraSection.classList.add('hidden');
    successSection.classList.add('hidden');
    
    switch(section) {
        case 'form':
            registrationFormSection.classList.remove('hidden');
            break;
        case 'camera':
            cameraSection.classList.remove('hidden');
            break;
        case 'success':
            successSection.classList.remove('hidden');
            break;
    }
}

/**
 * Start automatic face capture
 */
async function startAutomaticCapture() {
    isCapturing = true;
    
    while (isCapturing && captureCount < CONFIG.NUM_REGISTRATION_IMAGES) {
        try {
            progressText.textContent = `Capturing image ${captureCount + 1}...`;
            
            // Detect face and draw box
            const face = await detectFace(webcam);
            const ctx = overlay.getContext('2d');
            ctx.clearRect(0, 0, overlay.width, overlay.height);
            
            if (face) {
                drawFaceBox(overlay, face);
                
                // Generate embedding
                const embedding = await generateEmbedding(webcam);
                capturedEmbeddings.push(embedding);
                captureCount++;
                updateProgress();
                
                // Wait before next capture
                await new Promise(resolve => setTimeout(resolve, CONFIG.CAPTURE_INTERVAL_MS));
            } else {
                progressText.textContent = 'No face detected. Please position your face in frame.';
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
        } catch (error) {
            console.error('Capture error:', error);
            progressText.textContent = 'Capture failed. Retrying...';
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    
    // All captures done
    if (captureCount === CONFIG.NUM_REGISTRATION_IMAGES) {
        await submitRegistration();
    }
}

/**
 * Update progress bar
 */
function updateProgress() {
    const percentage = (captureCount / CONFIG.NUM_REGISTRATION_IMAGES) * 100;
    progressBar.style.width = `${percentage}%`;
    progressText.textContent = `${captureCount} / ${CONFIG.NUM_REGISTRATION_IMAGES} images captured`;
}

/**
 * Submit registration to backend
 */
async function submitRegistration() {
    isCapturing = false;
    stopWebcam();
    
    progressText.textContent = '📤 Submitting registration...';
    
    try {
        const response = await apiCall('/api/register', 'POST', {
            student_id: studentData.usn,
            registration_key: studentData.registrationKey,
            embeddings: capturedEmbeddings,
            name: studentData.name,
            semester: studentData.semester,
            section: studentData.section
        });
        
        // Save student data to cookies (don't save the key)
        saveStudentData({
            name: studentData.name,
            usn: studentData.usn,
            semester: studentData.semester,
            section: studentData.section
        });
        
        // Show success
        playSuccessSound();
        successMessage.innerHTML = `
            <strong>Name:</strong> ${studentData.name}<br>
            <strong>USN:</strong> ${studentData.usn}<br>
            <strong>Semester:</strong> ${studentData.semester}<br>
            <strong>Section:</strong> ${studentData.section}<br><br>
            You can now mark your attendance!
        `;
        showSection('success');
        
    } catch (error) {
        playErrorSound();
        showMessage(`Registration failed: ${error.message}`, true);
        showSection('form');
    }
}

/**
 * Cancel camera capture
 */
function cancelCamera() {
    isCapturing = false;
    stopWebcam();
    showSection('form');
}

/**
 * Hide message
 */
function hideMessage() {
    const messageDiv = document.getElementById('message');
    if (messageDiv) {
        messageDiv.style.display = 'none';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);
