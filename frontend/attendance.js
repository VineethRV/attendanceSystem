/**
 * Attendance page logic
 * Handles attendance marking with face verification
 */

let faceDetectionInterval = null;

// DOM Elements
const notLoggedInSection = document.getElementById('not-logged-in-section');
const studentInfoSection = document.getElementById('student-info-section');
const verificationSection = document.getElementById('verification-section');
const attendanceSuccessSection = document.getElementById('attendance-success-section');
const alreadyMarkedSection = document.getElementById('already-marked-section');

const attendanceStudentDetails = document.getElementById('attendance-student-details');
const verificationStatus = document.getElementById('verification-status');

const webcamVerify = document.getElementById('webcam-verify');
const overlayVerify = document.getElementById('overlay-verify');
const verifyBtn = document.getElementById('verify-btn');
const cancelVerifyBtn = document.getElementById('cancel-verify-btn');

const attendanceSuccessMessage = document.getElementById('attendance-success-message');
const alreadyMarkedMessage = document.getElementById('already-marked-message');

/**
 * Initialize attendance page
 */
async function init() {
    console.log('🚀 Initializing Attendance Page...');
    
    // Check if logged in
    const studentData = getStudentData();
    if (!studentData || !studentData.usn) {
        showSection('not-logged-in');
        return;
    }
    
    // Display student info
    displayStudentInfo(studentData);
    
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
    
    // Show verification section and start camera
    showSection('verification');
    await startVerification();
    
    // Set up event listeners
    setupEventListeners();
}

/**
 * Display student info
 */
function displayStudentInfo(studentData) {
    studentInfoSection.classList.remove('hidden');
    attendanceStudentDetails.innerHTML = `
        <div class="detail-row">
            <span class="detail-label">USN:</span>
            <span class="detail-value">${studentData.usn}</span>
        </div>
        ${studentData.name ? `
        <div class="detail-row">
            <span class="detail-label">Name:</span>
            <span class="detail-value">${studentData.name}</span>
        </div>
        ` : ''}
        ${studentData.semester ? `
        <div class="detail-row">
            <span class="detail-label">Semester:</span>
            <span class="detail-value">${studentData.semester}</span>
        </div>
        ` : ''}
        ${studentData.section ? `
        <div class="detail-row">
            <span class="detail-label">Section:</span>
            <span class="detail-value">${studentData.section}</span>
        </div>
        ` : ''}
    `;
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    verifyBtn.addEventListener('click', verifyAttendance);
    cancelVerifyBtn.addEventListener('click', cancelVerification);
}

/**
 * Show specific section
 */
function showSection(section) {
    notLoggedInSection.classList.add('hidden');
    verificationSection.classList.add('hidden');
    attendanceSuccessSection.classList.add('hidden');
    alreadyMarkedSection.classList.add('hidden');
    
    switch(section) {
        case 'not-logged-in':
            notLoggedInSection.classList.remove('hidden');
            studentInfoSection.classList.add('hidden');
            break;
        case 'verification':
            verificationSection.classList.remove('hidden');
            break;
        case 'success':
            attendanceSuccessSection.classList.remove('hidden');
            break;
        case 'already-marked':
            alreadyMarkedSection.classList.remove('hidden');
            break;
    }
}

/**
 * Start verification camera
 */
async function startVerification() {
    try {
        await startWebcam(webcamVerify);
        
        // Sync overlay with video
        webcamVerify.addEventListener('loadedmetadata', () => {
            overlayVerify.width = webcamVerify.videoWidth;
            overlayVerify.height = webcamVerify.videoHeight;
        });
        
        // Start face detection visualization
        visualizeFaceDetection();
        
    } catch (error) {
        showMessage(`Camera error: ${error.message}`, true);
    }
}

/**
 * Visualize face detection in real-time
 */
function visualizeFaceDetection() {
    faceDetectionInterval = setInterval(async () => {
        try {
            const face = await detectFace(webcamVerify);
            const ctx = overlayVerify.getContext('2d');
            ctx.clearRect(0, 0, overlayVerify.width, overlayVerify.height);
            
            if (face) {
                drawFaceBox(overlayVerify, face);
                verificationStatus.textContent = '✓ Face detected - Click "Mark Attendance"';
                verificationStatus.className = 'status-text status-ready';
            } else {
                verificationStatus.textContent = 'Position your face in the frame';
                verificationStatus.className = 'status-text';
            }
        } catch (error) {
            // Silently ignore detection errors during visualization
        }
    }, 200);
}

/**
 * Verify and mark attendance
 */
async function verifyAttendance() {
    const studentData = getStudentData();
    if (!studentData || !studentData.usn) {
        showMessage('Please login first', true);
        return;
    }
    
    verifyBtn.disabled = true;
    verifyBtn.textContent = 'Verifying...';
    verificationStatus.textContent = '🔄 Processing verification...';
    
    try {
        // Generate embedding from current frame
        const embedding = await generateEmbedding(webcamVerify);
        
        // Send verification request
        const response = await apiCall('/api/verify', 'POST', {
            student_id: studentData.usn,
            live_embedding: embedding
        });
        
        // Stop camera and face detection
        stopFaceDetection();
        stopWebcam();
        
        // Handle response
        if (response.status === 'success') {
            playSuccessSound();
            attendanceSuccessMessage.innerHTML = `
                <strong>USN:</strong> ${studentData.usn}<br>
                ${studentData.name ? `<strong>Name:</strong> ${studentData.name}<br>` : ''}
                <strong>Time:</strong> ${new Date().toLocaleString()}<br>
                <strong>Confidence:</strong> ${response.confidence ? (response.confidence * 100).toFixed(1) + '%' : 'Verified'}
            `;
            showSection('success');
        } else if (response.status === 'already_marked') {
            alreadyMarkedMessage.innerHTML = `
                You have already marked your attendance today.<br>
                <strong>Marked at:</strong> ${response.marked_at ? new Date(response.marked_at).toLocaleString() : 'Earlier today'}
            `;
            showSection('already-marked');
        } else if (response.status === 'not_registered') {
            showMessage('You are not registered. Please register first.', true);
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = '<span class="btn-icon">✓</span> Mark Attendance';
            await startVerification();
        } else {
            playErrorSound();
            showMessage(`Verification failed: ${response.message}`, true);
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = '<span class="btn-icon">✓</span> Mark Attendance';
        }
        
    } catch (error) {
        playErrorSound();
        showMessage(`Verification error: ${error.message}`, true);
        verifyBtn.disabled = false;
        verifyBtn.innerHTML = '<span class="btn-icon">✓</span> Mark Attendance';
    }
}

/**
 * Cancel verification
 */
function cancelVerification() {
    stopFaceDetection();
    stopWebcam();
    window.location.href = 'index.html';
}

/**
 * Stop face detection interval
 */
function stopFaceDetection() {
    if (faceDetectionInterval) {
        clearInterval(faceDetectionInterval);
        faceDetectionInterval = null;
    }
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
