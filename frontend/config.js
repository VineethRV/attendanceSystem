/**
 * Frontend Configuration
 * Adjust these values based on your setup
 */

const CONFIG = {
    // Backend API URL (use HTTPS for webcam access)
    BACKEND_URL: 'https://localhost:8000',
    
    // Face registration settings
    NUM_REGISTRATION_IMAGES: 5,
    CAPTURE_INTERVAL_MS: 1000,  // 1 second between captures
    
    // Video settings
    VIDEO_WIDTH: 640,
    VIDEO_HEIGHT: 480,
    
    // Cookie settings
    COOKIE_NAME: 'attendance_student_id',
    COOKIE_STUDENT_DATA: 'attendance_student_data',
    COOKIE_EXPIRY_DAYS: 365,
    
    // Model URLs (TensorFlow.js models)
    FACEMESH_MODEL_URL: 'https://cdn.jsdelivr.net/npm/@tensorflow-models/facemesh',
    
    // UI messages
    MESSAGES: {
        REGISTRATION_SUCCESS: 'Registration successful! You can now mark attendance.',
        REGISTRATION_FAILED: 'Registration failed. Please try again.',
        ATTENDANCE_SUCCESS: 'Attendance marked successfully!',
        ATTENDANCE_FAILED: 'Face verification failed. Please try again.',
        ATTENDANCE_ALREADY_MARKED: 'You have already marked attendance today.',
        NO_STUDENT_ID: 'Please register first or enter your student ID.',
        WEBCAM_ERROR: 'Unable to access webcam. Please check permissions.',
        PROCESSING: 'Processing...',
        FACE_NOT_DETECTED: 'No face detected. Please position your face clearly in the frame.',
        NOT_REGISTERED: 'Student not registered. Please register first.',
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
