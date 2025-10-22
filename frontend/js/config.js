// API Configuration
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

// Helper function to get auth headers
function getAuthHeaders() {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    return {
        'Authorization': `Bearer ${token}`
    };
}

// Helper function to make API calls
async function apiCall(url, options = {}) {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    
    const defaultOptions = {
        headers: {
            ...options.headers
        }
    };
    
    if (token && !options.skipAuth) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Don't add Content-Type for FormData
    if (!(options.body instanceof FormData) && options.headers) {
        defaultOptions.headers['Content-Type'] = 'application/json';
    }
    
    try {
        const response = await fetch(url, {
            ...defaultOptions,
            ...options
        });
        
        // Handle 401 Unauthorized
        if (response.status === 401 && !options.skipAuth) {
            // Token expired or invalid
            localStorage.clear();
            showSection('login');
            document.getElementById('main-nav').style.display = 'none';
            document.getElementById('user-info').style.display = 'none';
            showError('login-error', 'Session expired. Please login again.');
            return null;
        }
        
        const contentType = response.headers.get('content-type');
        
        // Handle file downloads
        if (contentType && contentType.includes('application/vnd.openxmlformats')) {
            return response.blob();
        }
        
        // Handle JSON responses
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || data.detail || 'API request failed');
            }
            
            return data;
        }
        
        // Handle other responses
        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || 'API request failed');
        }
        
        return response;
        
    } catch (error) {
        console.error('API call error:', error);
        throw error;
    }
}

// Helper function to show success message
function showSuccess(elementId, message) {
    const element = document.getElementById(elementId);
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
    element.className = 'error';
    element.textContent = message;
    element.style.display = 'block';
}

// Helper function to clear message
function clearMessage(elementId) {
    const element = document.getElementById(elementId);
    element.textContent = '';
    element.style.display = 'none';
}

// Helper function to format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Helper function to format currency
function formatCurrency(amount) {
    if (!amount) return '0.00';
    return parseFloat(amount).toFixed(2);
}

// Helper function to get status badge class
function getStatusBadgeClass(status) {
    const statusMap = {
        'PENDING': 'badge-pending',
        'PENDING_PD_APPROVAL': 'badge-pending',
        'PENDING_ADMIN_APPROVAL': 'badge-pending',
        'APPROVED': 'badge-approved',
        'REJECTED': 'badge-rejected',
        'DRAFT': 'badge-draft',
        'CLOSED': 'badge-closed'
    };
    return statusMap[status] || 'badge-pending';
}

// Helper function to show loading
function showLoading(elementId) {
    const element = document.getElementById(elementId);
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