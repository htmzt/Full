// API Configuration - FIXED VERSION
const API_BASE_URL = 'http://127.0.0.1:8000/api';

const API_ENDPOINTS = {
    // Authentication
    LOGIN: `${API_BASE_URL}/auth/login/`,
    LOGOUT: `${API_BASE_URL}/auth/logout/`,
    ME: `${API_BASE_URL}/auth/me/`,
    REGISTER: `${API_BASE_URL}/auth/register/`,
    CHANGE_PASSWORD: `${API_BASE_URL}/auth/change-password/`,
    USERS: `${API_BASE_URL}/auth/users/`,
    
    // Core - Upload & Merge
    UPLOAD_PO: `${API_BASE_URL}/core/upload/po/`,
    UPLOAD_ACCEPTANCE: `${API_BASE_URL}/core/upload/acceptance/`,
    MERGE_STATUS: `${API_BASE_URL}/core/merge/status/`,
    TRIGGER_MERGE: `${API_BASE_URL}/core/merge/trigger/`,
    MERGED_DATA: `${API_BASE_URL}/core/merged-data/`,
    EXPORT_MERGED_DATA: `${API_BASE_URL}/core/merged-data/export/`,
    UPLOAD_HISTORY: `${API_BASE_URL}/core/upload-history/`,
    MERGE_HISTORY: `${API_BASE_URL}/core/merge/history/`,
    
    // Assignments
    ASSIGNMENTS: `${API_BASE_URL}/assignments/`,
    CREATE_ASSIGNMENT: `${API_BASE_URL}/assignments/create/`,
    MY_ASSIGNMENTS: `${API_BASE_URL}/assignments/my-assignments/`,
    ASSIGNMENT_RESPOND: (id) => `${API_BASE_URL}/assignments/${id}/respond/`,
    CREATED_ASSIGNMENTS: `${API_BASE_URL}/assignments/`,  // Same as ASSIGNMENTS
    
    // NEW: Bulk assignment endpoints
    AVAILABLE_FOR_ASSIGNMENT: `${API_BASE_URL}/assignments/available-for-assignment/`,
    ASSIGNABLE_USERS: `${API_BASE_URL}/assignments/assignable-users/`,
    ASSIGNMENT_STATS: `${API_BASE_URL}/assignments/assignment-stats/`,
    
    // External POs
    EXTERNAL_POS: `${API_BASE_URL}/external-pos/`,
    CREATE_EXTERNAL_PO: `${API_BASE_URL}/external-pos/create/`,
    EXTERNAL_PO_DETAIL: (id) => `${API_BASE_URL}/external-pos/${id}/`,
    EXTERNAL_PO_SUBMIT: (id) => `${API_BASE_URL}/external-pos/${id}/submit/`,
    EXTERNAL_PO_DELETE: (id) => `${API_BASE_URL}/external-pos/${id}/delete/`,
    AVAILABLE_PO_LINES: `${API_BASE_URL}/external-pos/available-lines/`,
    PD_APPROVALS: `${API_BASE_URL}/external-pos/approvals/pd/`,
    ADMIN_APPROVALS: `${API_BASE_URL}/external-pos/approvals/admin/`,
    APPROVAL_RESPOND: (id) => `${API_BASE_URL}/external-pos/approvals/${id}/respond/`,
    SBC_WORK: `${API_BASE_URL}/external-pos/sbc/my-work/`,
    SBC_RESPOND: (id) => `${API_BASE_URL}/external-pos/sbc/${id}/respond/`,
};

// Storage keys
const STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    REFRESH_TOKEN: 'refresh_token',
    USER_DATA: 'user_data'
};

// ============================================================================
// API CALL FUNCTION - FIXED WITH PROPER ERROR HANDLING
// ============================================================================

async function apiCall(url, options = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };
    
    // Add auth token if not skipped
    if (!options.skipAuth) {
        const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
        if (token) {
            defaultHeaders['Authorization'] = `Bearer ${token}`;
        } else {
            // No token available
            console.error('No access token found - redirecting to login');
            
            // Only redirect if not already on login page
            const currentSection = document.querySelector('.section.active');
            if (currentSection && currentSection.id !== 'login-section') {
                localStorage.clear();
                showSection('login');
            }
            throw new Error('Not authenticated. Please login.');
        }
    }
    
    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...(options.headers || {})
        }
    };
    
    // Remove Content-Type for FormData
    if (options.body instanceof FormData) {
        delete config.headers['Content-Type'];
    }
    
    try {
        console.log(`[API] ${config.method || 'GET'} ${url}`);
        const response = await fetch(url, config);
        
        // Handle 401 Unauthorized - token expired or invalid
        if (response.status === 401) {
            console.error('401 Unauthorized - Session expired');
            
            // Clear storage and redirect to login
            localStorage.clear();
            sessionStorage.clear();
            
            // Show login section
            const loginSection = document.getElementById('login-section');
            if (loginSection) {
                showSection('login');
                
                // Show error message
                const errorDiv = document.getElementById('login-error');
                if (errorDiv) {
                    errorDiv.textContent = 'Session expired. Please login again.';
                    errorDiv.style.display = 'block';
                }
            }
            
            throw new Error('Session expired. Please login again.');
        }
        
        // Handle 403 Forbidden - no permission
        if (response.status === 403) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Permission denied');
        }
        
        // Handle 404 Not Found
        if (response.status === 404) {
            throw new Error('Resource not found');
        }
        
        // Handle other errors
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.error || errorData.detail || errorData.message || `HTTP Error ${response.status}`;
            throw new Error(errorMessage);
        }
        
        // Return response based on content type
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            console.log(`[API] Success:`, data);
            return data;
        }
        
        // For file downloads or other content types
        return response;
        
    } catch (error) {
        console.error(`[API] Error:`, error);
        throw error;
    }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

// Helper function to show success message
function showSuccess(elementId, message) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.className = 'success';
    element.textContent = message;
    element.style.display = 'block';
    
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

// Helper function to show error message
function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.className = 'error';
    element.textContent = message;
    element.style.display = 'block';
}

// Helper function to clear message
function clearMessage(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.textContent = '';
    element.style.display = 'none';
}

// Helper function to format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch (e) {
        return dateString;
    }
}

// Helper function to format currency
function formatCurrency(amount) {
    if (!amount && amount !== 0) return '0.00';
    try {
        return parseFloat(amount).toFixed(2);
    } catch (e) {
        return amount;
    }
}

// Helper function to escape HTML (prevent XSS)
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Helper function to get status badge class
function getStatusBadgeClass(status) {
    if (!status) return 'badge-pending';
    
    const statusMap = {
        'PENDING': 'badge-pending',
        'PENDING_PD_APPROVAL': 'badge-pending',
        'PENDING_ADMIN_APPROVAL': 'badge-pending',
        'APPROVED': 'badge-approved',
        'REJECTED': 'badge-rejected',
        'DRAFT': 'badge-draft',
        'CLOSED': 'badge-closed',
        'COMPLETED': 'badge-approved',
        'FAILED': 'badge-rejected',
        'OPEN': 'badge-pending'
    };
    
    return statusMap[status.toUpperCase()] || 'badge-pending';
}

// Helper function to show loading
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.innerHTML = '<div class="loading"></div> Loading...';
}

// Helper function to download file
function downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Helper function to check if user is authenticated
function isAuthenticated() {
    return !!localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

// Helper function to get user data
function getUserData() {
    const userData = localStorage.getItem(STORAGE_KEYS.USER_DATA);
    return userData ? JSON.parse(userData) : null;
}

// Helper function to check user permission
function hasPermission(permissionName) {
    const user = getUserData();
    if (!user) return false;
    return user[permissionName] === true;
}

// Debug helper - log API calls (set to false in production)
const DEBUG_MODE = true;

if (DEBUG_MODE) {
    console.log('[CONFIG] API Base URL:', API_BASE_URL);
    console.log('[CONFIG] Storage Keys:', STORAGE_KEYS);
    console.log('[CONFIG] Authenticated:', isAuthenticated());
}