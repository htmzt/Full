// User management functions

async function createUser(event) {
    event.preventDefault();
    
    const email = document.getElementById('user-email').value;
    const password = document.getElementById('user-password').value;
    const passwordConfirm = document.getElementById('user-password-confirm').value;
    const fullName = document.getElementById('user-fullname').value;
    const role = document.getElementById('user-role').value;
    const phone = document.getElementById('user-phone').value;
    const sbcCompany = document.getElementById('user-sbc-company').value;
    
    if (password !== passwordConfirm) {
        showError('user-create-result', 'Passwords do not match');
        return;
    }
    
    const resultDiv = document.getElementById('user-create-result');
    resultDiv.innerHTML = '<div class="loading"></div> Creating user...';
    
    const userData = {
        email: email,
        password: password,
        password_confirm: passwordConfirm,
        full_name: fullName,
        role: role,
        phone: phone
    };
    
    if (role === 'SBC' && sbcCompany) {
        userData.sbc_company_name = sbcCompany;
    }
    
    try {
        const data = await apiCall(API_ENDPOINTS.REGISTER, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });
        
        if (data) {
            resultDiv.innerHTML = `
                <div class="success">
                    <h4>✅ User Created!</h4>
                    <p><strong>Email:</strong> ${data.email}</p>
                    <p><strong>Full Name:</strong> ${data.full_name}</p>
                    <p><strong>Role:</strong> ${data.role}</p>
                    ${data.sbc_code ? '<p><strong>SBC Code:</strong> ' + data.sbc_code + '</p>' : ''}
                </div>
            `;
            
            // Clear form
            document.getElementById('create-user-form').reset();
            
            // Reload users list
            loadUsers();
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Failed to create user: ${error.message}</div>`;
    }
}

async function loadUsers() {
    const listDiv = document.getElementById('users-list');
    listDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.USERS, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '<table><thead><tr>';
            html += '<th>Email</th>';
            html += '<th>Full Name</th>';
            html += '<th>Role</th>';
            html += '<th>SBC Code</th>';
            html += '<th>Status</th>';
            html += '<th>Created</th>';
            html += '</tr></thead><tbody>';
            
            data.results.forEach(user => {
                html += '<tr>';
                html += `<td>${user.email}</td>`;
                html += `<td>${user.full_name}</td>`;
                html += `<td><span class="badge badge-pending">${user.role}</span></td>`;
                html += `<td>${user.sbc_code || 'N/A'}</td>`;
                html += `<td>${user.is_active ? '<span class="badge badge-approved">Active</span>' : '<span class="badge badge-rejected">Inactive</span>'}</td>`;
                html += `<td>${formatDate(user.created_at)}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="empty-state"><p>No users found</p></div>';
        }
    } catch (error) {
        listDiv.innerHTML = `<div class="error">Failed to load users: ${error.message}</div>`;
    }
}