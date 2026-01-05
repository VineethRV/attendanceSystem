/**
 * Utility functions for cookie management, API calls, and embedding generation
 */

/**
 * Cookie Management
 */
function setCookie(name, value, days) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires.toUTCString()};path=/;secure;samesite=strict`;
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length, c.length));
    }
    return null;
}

function deleteCookie(name) {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
}

/**
 * Get stored student ID from cookie (legacy support)
 */
function getStudentId() {
    const studentData = getStudentData();
    if (studentData && studentData.usn) {
        return studentData.usn;
    }
    return getCookie(CONFIG.COOKIE_NAME);
}

/**
 * Save student ID to cookie (legacy support)
 */
function saveStudentId(studentId) {
    setCookie(CONFIG.COOKIE_NAME, studentId, CONFIG.COOKIE_EXPIRY_DAYS);
}

/**
 * Get complete student data from cookie
 * Returns: { name, usn, semester, section }
 */
function getStudentData() {
    const data = getCookie(CONFIG.COOKIE_STUDENT_DATA);
    if (data) {
        try {
            return JSON.parse(data);
        } catch (e) {
            console.error('Failed to parse student data:', e);
            return null;
        }
    }
    // Legacy fallback - check old cookie
    const legacyId = getCookie(CONFIG.COOKIE_NAME);
    if (legacyId) {
        return { usn: legacyId, name: '', semester: '', section: '' };
    }
    return null;
}

/**
 * Save complete student data to cookie
 * @param {Object} data - { name, usn, semester, section }
 */
function saveStudentData(data) {
    setCookie(CONFIG.COOKIE_STUDENT_DATA, JSON.stringify(data), CONFIG.COOKIE_EXPIRY_DAYS);
    // Also save USN to legacy cookie for backward compatibility
    if (data.usn) {
        saveStudentId(data.usn);
    }
}

/**
 * Clear student data from cookies
 */
function clearStudentData() {
    deleteCookie(CONFIG.COOKIE_STUDENT_DATA);
    deleteCookie(CONFIG.COOKIE_NAME);
}

/**
 * Display message to user
 */
function showMessage(message, isError = false) {
    const messageDiv = document.getElementById('message');
    if (messageDiv) {
        messageDiv.textContent = message;
        messageDiv.className = isError ? 'message error' : 'message success';
        messageDiv.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}

/**
 * API Call Helper
 */
async function apiCall(endpoint, method = 'GET', data = null, headers = {}) {
    const url = `${CONFIG.BACKEND_URL}${endpoint}`;
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            ...headers
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        const responseData = await response.json();
        
        if (!response.ok) {
            throw new Error(responseData.message || responseData.detail?.message || 'API call failed');
        }
        
        return responseData;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Webcam Management
 */
let currentStream = null;

async function startWebcam(videoElement) {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: CONFIG.VIDEO_WIDTH,
                height: CONFIG.VIDEO_HEIGHT,
                facingMode: 'user'
            }
        });
        
        videoElement.srcObject = stream;
        currentStream = stream;
        
        return new Promise((resolve) => {
            videoElement.onloadedmetadata = () => {
                videoElement.play();
                resolve();
            };
        });
    } catch (error) {
        console.error('Webcam Error:', error);
        throw new Error(CONFIG.MESSAGES.WEBCAM_ERROR);
    }
}

function stopWebcam() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
}

/**
 * Face Detection and Embedding Generation
 * Uses TensorFlow.js with FaceNet/MobileFaceNet model
 */

let faceDetectionModel = null;
let faceRecognitionModel = null;

/**
 * Load TensorFlow.js models
 */
async function loadModels() {
    if (faceDetectionModel && faceRecognitionModel) {
        return; // Already loaded
    }
    
    console.log('Loading models...');
    
    // Check if blazeface is available
    if (typeof blazeface === 'undefined') {
        console.warn('BlazeFace not loaded. Face detection may not work.');
        // Create a mock model for pages that don't need face detection
        faceDetectionModel = {
            estimateFaces: async () => []
        };
        faceRecognitionModel = {
            predict: () => null
        };
        return;
    }
    
    try {
        // Load BlazeFace for face detection
        faceDetectionModel = await blazeface.load();
        console.log('✅ Face detection model loaded');
        
        // Load FaceNet-like model for embeddings
        // Note: Using MobileFaceNet as a lightweight alternative
        // You can replace this with a custom trained ArcFace model
        try {
            faceRecognitionModel = await tf.loadGraphModel(
                'https://tfhub.dev/tensorflow/tfjs-model/facenet/1/default/1',
                { fromTFHub: true }
            );
            console.log('✅ Face recognition model loaded');
        } catch (faceNetError) {
            console.warn('FaceNet model failed to load, using fallback:', faceNetError);
            // Use a simplified embedding approach as fallback
            faceRecognitionModel = null;
        }
        
    } catch (error) {
        console.error('Model loading error:', error);
        // Fallback: use a simpler approach with pre-trained models
        console.log('Using fallback model...');
        try {
            faceDetectionModel = await blazeface.load();
        } catch (fallbackError) {
            console.error('Fallback model also failed:', fallbackError);
            faceDetectionModel = {
                estimateFaces: async () => []
            };
        }
    }
}

/**
 * Detect face in video frame
 */
async function detectFace(videoElement) {
    if (!faceDetectionModel) {
        await loadModels();
    }
    
    const predictions = await faceDetectionModel.estimateFaces(videoElement, false);
    
    if (predictions.length === 0) {
        return null;
    }
    
    // Return the first detected face
    return predictions[0];
}

/**
 * Generate face embedding from video frame
 * This is a simplified version - replace with actual ArcFace model
 */
async function generateEmbedding(videoElement) {
    // Detect face first
    const face = await detectFace(videoElement);
    
    if (!face) {
        throw new Error('No face detected');
    }
    
    // Create a canvas to extract face region
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Get face bounding box
    const [x, y] = face.topLeft;
    const [x2, y2] = face.bottomRight;
    const width = x2 - x;
    const height = y2 - y;
    
    // Add padding
    const padding = 30;
    const faceX = Math.max(0, x - padding);
    const faceY = Math.max(0, y - padding);
    const faceWidth = width + 2 * padding;
    const faceHeight = height + 2 * padding;
    
    canvas.width = 160;  // FaceNet input size
    canvas.height = 160;
    
    // Draw face region
    ctx.drawImage(
        videoElement,
        faceX, faceY, faceWidth, faceHeight,
        0, 0, 160, 160
    );
    
    // Convert to tensor
    const imageTensor = tf.browser.fromPixels(canvas)
        .toFloat()
        .div(255.0)
        .sub(0.5)
        .mul(2.0)  // Normalize to [-1, 1]
        .expandDims(0);
    
    // Generate embedding
    // For demo: using a simple CNN-based approach
    // Replace this with actual ArcFace model inference
    let embedding;
    
    if (faceRecognitionModel) {
        const embeddingTensor = await faceRecognitionModel.predict(imageTensor);
        embedding = await embeddingTensor.data();
    } else {
        // Fallback: Generate a pseudo-embedding using CNN features
        embedding = await generatePseudoEmbedding(imageTensor);
    }
    
    // Clean up tensors
    imageTensor.dispose();
    
    // Normalize embedding (L2 normalization)
    const embeddingArray = Array.from(embedding);
    const norm = Math.sqrt(embeddingArray.reduce((sum, val) => sum + val * val, 0));
    const normalizedEmbedding = embeddingArray.map(val => val / norm);
    
    return normalizedEmbedding;
}

/**
 * Generate pseudo-embedding using MobileNet features
 * This is a fallback for demo purposes
 * Replace with actual ArcFace model for production
 */
async function generatePseudoEmbedding(imageTensor) {
    // Use MobileNet as a feature extractor
    const mobilenet = await tf.loadLayersModel(
        'https://storage.googleapis.com/tfjs-models/tfjs/mobilenet_v1_0.25_224/model.json'
    );
    
    // Resize to MobileNet input size
    const resized = tf.image.resizeBilinear(imageTensor, [224, 224]);
    
    // Get features from second-to-last layer
    const features = mobilenet.predict(resized);
    const embedding = await features.data();
    
    // Clean up
    resized.dispose();
    features.dispose();
    
    // Pad or truncate to 512 dimensions
    const targetDim = 512;
    const embeddingArray = Array.from(embedding);
    
    if (embeddingArray.length > targetDim) {
        return embeddingArray.slice(0, targetDim);
    } else {
        // Pad with zeros
        return [...embeddingArray, ...Array(targetDim - embeddingArray.length).fill(0)];
    }
}

/**
 * Validate student ID format
 */
function validateStudentId(studentId) {
    const pattern = /^1RV23CS(0[0-9]{2}|[1-3][0-9]{2}|4[0-1][0-9]|420)$/;
    return pattern.test(studentId);
}

/**
 * Draw face bounding box on canvas (for visualization)
 */
function drawFaceBox(canvas, face) {
    const ctx = canvas.getContext('2d');
    const [x, y] = face.topLeft;
    const [x2, y2] = face.bottomRight;
    const width = x2 - x;
    const height = y2 - y;
    
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, width, height);
}
