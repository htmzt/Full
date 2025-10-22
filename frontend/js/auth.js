// Authentication functions

async function login(event) {
    event.preventDefault();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    clearMessage('login-error');
    
    try {
        const data = await apiCall(API_ENDPOINTS.LOGIN, {
            method: 'POST',
            skipAuth: true,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });
        
        if (data) {
            // Store tokens and user data
            localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
            localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
            localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(data.user));
            
            // Update UI
            document.getElementById('user-email').textContent = data.user.email;
            document.getElementById('user-role').textContent = data.user.role;
            document.getElementById('user-info').style.display = 'flex';
            document.getElementById('main-nav').style.display = 'block';
            
            // Show dashboard
            showSection('dashboard');
            loadDashboard();
            
            // Clear form
            document.getElementById('login-form').reset();
        }
    } catch (error) {
        showError('login-error', error.message || 'Login failed');
    }
}

function logout() {
    // Clear local storage
    localStorage.clear();
    
    // Hide navigation and user info
    document.getElementById('main-nav').style.display = 'none';
    document.getElementById('user-info').style.display = 'none';
    
    // Show login section
    showSection('login');
}

async function getCurrentUser() {
    try {
        const data = await apiCall(API_ENDPOINTS.ME, {
            method: 'GET'
        });
        
        if (data) {
            localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(data));
            return data;
        }
    } catch (error) {
        console.error('Failed to get current user:', error);
        return null;
    }
}

function getUserData() {
    const userData = localStorage.getItem(STORAGE_KEYS.USER_DATA);
    return userData ? JSON.parse(userData) : null;
}

function isAuthenticated() {
    return !!localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

// Check authentication on page load
window.addEventListener('DOMContentLoaded', async () => {
    if (isAuthenticated()) {
        const user = getUserData();
        if (user) {
            document.getElementById('user-email').textContent = user.email;
            document.getElementById('user-role').textContent = user.role;
            document.getElementById('user-info').style.display = 'flex';
            document.getElementById('main-nav').style.display = 'block';
            showSection('dashboard');
            loadDashboard();
        }
    }
});