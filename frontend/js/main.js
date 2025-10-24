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
        
        // Load data when section is shown
        if (sectionName === 'assignments') {
            const user = getUserData();
            if (user && (user.can_assign_pos)) {
                loadAssignmentStats();
                loadAvailablePOLinesForAssignment();
                loadAssignableUsers();
            }
            loadMyAssignments();
            loadCreatedAssignments();
        }
    }
}
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
    }
}

async function loadDashboard() {
    const user = getUserData();
    
    // Display current user details
    const userDetails = document.getElementById('current-user-details');
    if (user) {
        userDetails.innerHTML = `
            <p><strong>Email:</strong> ${user.email}</p>
            <p><strong>Full Name:</strong> ${user.full_name}</p>
            <p><strong>Role:</strong> ${user.role}</p>
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
    }
    
    // Load stats
    try {
        // Get merged data stats
        const mergedData = await apiCall(API_ENDPOINTS.MERGED_DATA, {
            method: 'GET'
        });
        
        if (mergedData && mergedData.results) {
            document.getElementById('stat-total-pos').textContent = mergedData.count || 0;
            
            const assignedCount = mergedData.results.filter(po => po.is_assigned).length;
            document.getElementById('stat-assigned-pos').textContent = assignedCount;
            
            const externalCount = mergedData.results.filter(po => po.has_external_po).length;
            document.getElementById('stat-external-pos').textContent = externalCount;
        }
        
        // Get pending approvals count
        if (user.can_approve_level_1 || user.can_approve_level_2) {
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
            
            document.getElementById('stat-pending-approvals').textContent = pendingCount;
        }
        
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// Toggle SBC company name field based on role selection
document.addEventListener('DOMContentLoaded', () => {
    const roleSelect = document.getElementById('user-role');
    if (roleSelect) {
        roleSelect.addEventListener('change', function() {
            const sbcGroup = document.getElementById('sbc-company-group');
            if (this.value === 'SBC') {
                sbcGroup.style.display = 'block';
                document.getElementById('user-sbc-company').required = true;
            } else {
                sbcGroup.style.display = 'none';
                document.getElementById('user-sbc-company').required = false;
            }
        });
    }
});