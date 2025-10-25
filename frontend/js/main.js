// Main application functions

function showSection(sectionName) {
    // Hide all sections
    const sections = document.querySelectorAll('.section');
    sections.forEach(section => {
        section.classList.remove('active');
    });
    
    // Show selected section
    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.classList.add('active');
        
        // Trigger custom event for section activation
        const event = new CustomEvent('showSection', { detail: sectionName });
        document.dispatchEvent(event);
    } else {
        console.warn(`Section ${sectionName}-section not found`);
    }
}

// Load dashboard data
async function loadDashboard() {
    const user = getUserData();
    const userDetails = document.getElementById('current-user-details');
    
    // Display current user details
    if (user && userDetails) {
        userDetails.innerHTML = `
            <p><strong>Email:</strong> ${escapeHtml(user.email)}</p>
            <p><strong>Full Name:</strong> ${escapeHtml(user.full_name)}</p>
            <p><strong>Role:</strong> ${escapeHtml(user.role)}</p>
            <p><strong>Permissions:</strong></p>
            <ul>
                ${user.can_upload_files ? '<li>✅ Can upload files</li>' : ''}
                ${user.can_trigger_merge ? '<li>✅ Can trigger merge</li>' : ''}
                ${user.can_assign_pos ? '<li>✅ Can assign POs</li>' : ''}
                ${user.can_view_all_pos ? '<li>✅ Can view all POs</li>' : ''}
                ${user.can_create_external_po_any ? '<li>✅ Can create External POs (any)</li>' : ''}
                ${user.can_create_external_po_assigned ? '<li>✅ Can create External POs (assigned)</li>' : ''}
                ${user.can_approve_level_1 ? '<li>✅ Can approve Level 1 (PD)</li>' : ''}
                ${user.can_approve_level_2 ? '<li>✅ Can approve Level 2 (Admin)</li>' : ''}
                ${user.can_manage_users ? '<li>✅ Can manage users</li>' : ''}
                ${user.can_export_data ? '<li>✅ Can export data</li>' : ''}
                ${user.can_view_sbc_work ? '<li>✅ Can view SBC work</li>' : ''}
            </ul>
        `;
    } else if (userDetails) {
        userDetails.innerHTML = '<p class="error">⚠️ User data not available</p>';
    }
    
    try {
        const mergedData = await apiCall(API_ENDPOINTS.MERGED_DATA, {
            method: 'GET'
        });
        
        if (mergedData && mergedData.results) {
            document.getElementById('stat-total-pos').textContent = mergedData.count || 0;
            
            const assignedCount = mergedData.results.filter(po => po.is_assigned).length;
            document.getElementById('stat-assigned-pos').textContent = assignedCount;
            
            const externalCount = mergedData.results.filter(po => po.has_external_po).length;
            document.getElementById('stat-external-pos').textContent = externalCount;
        } else {
            throw new Error('Invalid merged data response');
        }
        
        if (user && (user.can_approve_level_1 || user.can_approve_level_2)) {
            let pendingCount = 0;
            
            if (user.can_approve_level_1) {
                const pdApprovals = await apiCall(API_ENDPOINTS.PD_APPROVALS, {
                    method: 'GET'
                });
                if (pdApprovals && pdApprovals.results) {
                    pendingCount += pdApprovals.results.length;
                }
            }
            
            if (user.can_approve_level_2) {
                const adminApprovals = await apiCall(API_ENDPOINTS.ADMIN_APPROVALS, {
                    method: 'GET'
                });
                if (adminApprovals && adminApprovals.results) {
                    pendingCount += adminApprovals.results.length;
                }
            }
            
            const pendingElement = document.getElementById('stat-pending-approvals');
            if (pendingElement) {
                pendingElement.textContent = pendingCount;
            }
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        const errorDiv = document.getElementById('dashboard-error');
        if (errorDiv) {
            errorDiv.innerHTML = `<p class="error">⚠️ Failed to load dashboard stats: ${error.message}</p>`;
        }
    }
}

// Toggle SBC company name field based on role selection
document.addEventListener('DOMContentLoaded', () => {
    const roleSelect = document.getElementById('user-role');
    if (roleSelect) {
        roleSelect.addEventListener('change', function() {
            const sbcGroup = document.getElementById('sbc-company-group');
            if (sbcGroup) {
                if (this.value === 'SBC') {
                    sbcGroup.style.display = 'block';
                    const sbcCompanyInput = document.getElementById('user-sbc-company');
                    if (sbcCompanyInput) {
                        sbcCompanyInput.required = true;
                    }
                } else {
                    sbcGroup.style.display = 'none';
                    const sbcCompanyInput = document.getElementById('user-sbc-company');
                    if (sbcCompanyInput) {
                        sbcCompanyInput.required = false;
                    }
                }
            }
        });
    }
});

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}