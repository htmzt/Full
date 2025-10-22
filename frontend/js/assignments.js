// Assignment functions

async function loadUsersForAssignment() {
    try {
        const data = await apiCall(API_ENDPOINTS.USERS, {
            method: 'GET'
        });
        
        if (data && data.results) {
            const select = document.getElementById('assignment-user');
            select.innerHTML = '<option value="">Select User...</option>';
            
            // Filter users by role (ADMIN, PD, PM)
            const validRoles = ['ADMIN', 'PD', 'PM'];
            data.results
                .filter(user => validRoles.includes(user.role))
                .forEach(user => {
                    select.innerHTML += `<option value="${user.id}">${user.full_name} (${user.role})</option>`;
                });
        }
    } catch (error) {
        console.error('Failed to load users:', error);
    }
}

async function createAssignment(event) {
    event.preventDefault();
    
    const poIdsInput = document.getElementById('assignment-po-ids').value;
    const userId = document.getElementById('assignment-user').value;
    const notes = document.getElementById('assignment-notes').value;
    
    // Parse PO IDs (comma separated)
    const poIds = poIdsInput.split(',').map(id => id.trim()).filter(id => id);
    
    if (poIds.length === 0) {
        showError('assignment-create-result', 'Please enter at least one PO ID');
        return;
    }
    
    const resultDiv = document.getElementById('assignment-create-result');
    resultDiv.innerHTML = '<div class="loading"></div> Creating assignment...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.CREATE_ASSIGNMENT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                po_ids: poIds,
                assigned_to_user_id: userId,
                assignment_notes: notes
            })
        });
        
        if (data) {
            resultDiv.innerHTML = `
                <div class="success">
                    <h4>✅ Assignment Created!</h4>
                    <p><strong>Assignment ID:</strong> ${data.id}</p>
                    <p><strong>PO Count:</strong> ${data.po_count}</p>
                    <p><strong>Assigned To:</strong> ${data.assigned_to_name}</p>
                    <p><strong>Status:</strong> ${data.status}</p>
                </div>
            `;
            
            // Clear form
            document.getElementById('create-assignment-form').reset();
            
            // Reload assignments
            loadCreatedAssignments();
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Failed to create assignment: ${error.message}</div>`;
    }
}

async function loadMyAssignments() {
    const listDiv = document.getElementById('my-assignments');
    listDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.MY_ASSIGNMENTS, {
            method: 'GET'
        });
        
        if (data) {
            let html = '';
            
            // Pending assignments
            if (data.pending && data.pending.length > 0) {
                html += '<h4>Pending</h4>';
                data.pending.forEach(assignment => {
                    html += renderAssignmentCard(assignment, true);
                });
            }
            
            // Approved assignments
            if (data.approved && data.approved.length > 0) {
                html += '<h4>Approved</h4>';
                data.approved.forEach(assignment => {
                    html += renderAssignmentCard(assignment, false);
                });
            }
            
            // Rejected assignments
            if (data.rejected && data.rejected.length > 0) {
                html += '<h4>Rejected</h4>';
                data.rejected.forEach(assignment => {
                    html += renderAssignmentCard(assignment, false);
                });
            }
            
            if (html === '') {
                html = '<div class="empty-state"><p>No assignments found</p></div>';
            }
            
            listDiv.innerHTML = html;
        }
    } catch (error) {
        listDiv.innerHTML = `<div class="error">Failed to load assignments: ${error.message}</div>`;
    }
}

async function loadCreatedAssignments() {
    const listDiv = document.getElementById('created-assignments');
    listDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.ASSIGNMENTS, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '';
            data.results.forEach(assignment => {
                html += renderAssignmentCard(assignment, false);
            });
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="empty-state"><p>No assignments found</p></div>';
        }
    } catch (error) {
        listDiv.innerHTML = `<div class="error">Failed to load assignments: ${error.message}</div>`;
    }
}

function renderAssignmentCard(assignment, showActions) {
    let html = '<div class="card">';
    html += `<h4>Assignment #${assignment.id.substring(0, 8)}</h4>`;
    html += `<p><strong>PO Count:</strong> ${assignment.po_count}</p>`;
    html += `<p><strong>Assigned To:</strong> ${assignment.assigned_to_name}</p>`;
    html += `<p><strong>Assigned By:</strong> ${assignment.assigned_by_name}</p>`;
    html += `<p><strong>Status:</strong> <span class="badge badge-${assignment.status.toLowerCase()}">${assignment.status}</span></p>`;
    html += `<p><strong>Created:</strong> ${formatDate(assignment.created_at)}</p>`;
    
    if (assignment.assignment_notes) {
        html += `<p><strong>Notes:</strong> ${assignment.assignment_notes}</p>`;
    }
    
    if (assignment.rejection_reason) {
        html += `<p><strong>Rejection Reason:</strong> ${assignment.rejection_reason}</p>`;
    }
    
    if (showActions && assignment.status === 'PENDING') {
        html += '<div class="card-actions">';
        html += `<button onclick="respondToAssignment('${assignment.id}', 'APPROVE')" class="btn-primary">Approve</button>`;
        html += `<button onclick="respondToAssignment('${assignment.id}', 'REJECT')" class="btn-danger">Reject</button>`;
        html += '</div>';
    }
    
    html += '</div>';
    return html;
}

async function respondToAssignment(assignmentId, action) {
    let rejectionReason = '';
    
    if (action === 'REJECT') {
        rejectionReason = prompt('Please provide a rejection reason:');
        if (!rejectionReason) {
            return;
        }
    }
    
    try {
        const data = await apiCall(API_ENDPOINTS.ASSIGNMENT_RESPOND(assignmentId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: action,
                rejection_reason: rejectionReason
            })
        });
        
        if (data) {
            alert(`Assignment ${action.toLowerCase()}ed successfully!`);
            loadMyAssignments();
        }
    } catch (error) {
        alert(`Failed to respond to assignment: ${error.message}`);
    }
}

// Load users when assignments section is shown
document.addEventListener('DOMContentLoaded', () => {
    loadUsersForAssignment();
});