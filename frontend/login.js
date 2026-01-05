/**
 * Login page logic
 * Handles student login and session management
 */

// DOM Elements
const loginSection = document.getElementById('login-section');
const loggedInSection = document.getElementById('logged-in-section');
const loginForm = document.getElementById('login-form');
const loginUsnInput = document.getElementById('login-usn');
const studentDetails = document.getElementById('student-details');
const logoutBtn = document.getElementById('logout-btn');

/**
 * Initialize login page
 */
function init() {
    console.log('🚀 Initializing Login Page...');
    
    // Check if already logged in
    const studentData = getStudentData();
    if (studentData && studentData.usn) {
        showLoggedInView(studentData);
    } else {
        showLoginView();
    }
    
    // Set up event listeners
    setupEventListeners();
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    loginForm.addEventListener('submit', handleLogin);
    logoutBtn.addEventListener('click', handleLogout);
}

/**
 * Handle login form submission
 */
function handleLogin(e) {
    e.preventDefault();
    
    const usn = loginUsnInput.value.trim().toUpperCase();
    
    if (!usn) {
        showMessage('Please enter your USN', true);
        return;
    }
    
    // Check if there's stored student data matching this USN
    const existingData = getStudentData();
    
    if (existingData && existingData.usn === usn) {
        // User is logging back in with their registered USN
        showMessage('Login successful!', false);
        showLoggedInView(existingData);
    } else if (existingData && existingData.usn !== usn) {
        // Different USN - update the stored data
        const newData = {
            usn: usn,
            name: '',
            semester: '',
            section: ''
        };
        saveStudentData(newData);
        showMessage('Logged in with new USN. Some details may be missing.', false);
        showLoggedInView(newData);
    } else {
        // No existing data - create new session
        const newData = {
            usn: usn,
            name: '',
            semester: '',
            section: ''
        };
        saveStudentData(newData);
        showMessage('Logged in! If you have not registered, please register first for face verification.', false);
        showLoggedInView(newData);
    }
}

/**
 * Handle logout
 */
function handleLogout() {
    clearStudentData();
    showMessage('Logged out successfully', false);
    showLoginView();
    loginUsnInput.value = '';
}

/**
 * Show login view
 */
function showLoginView() {
    loginSection.classList.remove('hidden');
    loggedInSection.classList.add('hidden');
}

/**
 * Show logged in view
 */
function showLoggedInView(studentData) {
    loginSection.classList.add('hidden');
    loggedInSection.classList.remove('hidden');
    
    // Display student details
    studentDetails.innerHTML = `
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

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);
