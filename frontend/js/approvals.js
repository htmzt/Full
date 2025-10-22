// Approval functions

async function loadPDApprovals() {
    const listDiv = document.getElementById('pd-approvals-list');
    listDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.PD_APPROVALS, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '';
            data.results.forEach(externalPO => {
                html += renderApprovalCard(externalPO, 'PD');
            });
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="empty-state"><p>No pending PD approvals</p></div>';
        }
    } catch (error) {
        listDiv.innerHTML = `<div class="error">Failed to load PD approvals: ${error.message}</div>`;
    }
}

async function loadAdminApprovals() {
    const listDiv = document.getElementById('admin-approvals-list');
    listDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.ADMIN_APPROVALS, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '';
            data.results.forEach(externalPO => {
                html += renderApprovalCard(externalPO, 'ADMIN');
            });
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="empty-state"><p>No pending Admin approvals</p></div>';
        }
    } catch (error) {
        listDiv.innerHTML = `<div class="error">Failed to load Admin approvals: ${error.message}</div>`;
    }
}

async function loadSBCWork() {
    const listDiv = document.getElementById('sbc-work-list');
    listDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.SBC_WORK, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '';
            data.results.forEach(externalPO => {
                html += renderSBCWorkCard(externalPO);
            });
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="empty-state"><p>No approved work assigned</p></div>';
        }
    } catch (error) {
        listDiv.innerHTML = `<div class="error">Failed to load SBC work: ${error.message}</div>`;
    }
}

function renderApprovalCard(externalPO, approverLevel) {
    let html = '<div class="card">';
    html += `<h4>${externalPO.internal_po_id}</h4>`;
    html += `<p><strong>Status:</strong> <span class="badge badge-${getStatusBadgeClass(externalPO.status)}">${externalPO.status}</span></p>`;
    html += `<p><strong>PO Line Count:</strong> ${externalPO.po_line_count}</p>`;
    html += `<p><strong>Assigned to SBC:</strong> ${externalPO.assigned_to_sbc_name}</p>`;
    html += `<p><strong>Estimated Amount:</strong> ${formatCurrency(externalPO.estimated_total_amount)}</p>`;
    html += `<p><strong>Submitted:</strong> ${formatDate(externalPO.submitted_at)}</p>`;
    
    html += '<div class="card-actions">';
    html += `<button onclick="approveExternalPO('${externalPO.id}')" class="btn-primary">Approve</button>`;
    html += `<button onclick="rejectExternalPO('${externalPO.id}')" class="btn-danger">Reject</button>`;
    html += `<button onclick="viewExternalPODetails('${externalPO.id}')">View Details</button>`;
    html += '</div>';
    html += '</div>';
    
    return html;
}

function renderSBCWorkCard(externalPO) {
    let html = '<div class="card">';
    html += `<h4>${externalPO.internal_po_id}</h4>`;
    html += `<p><strong>Status:</strong> <span class="badge badge-approved">${externalPO.status}</span></p>`;
    html += `<p><strong>PO Line Count:</strong> ${externalPO.po_line_count}</p>`;
    html += `<p><strong>Estimated Amount:</strong> ${formatCurrency(externalPO.estimated_total_amount)}</p>`;
    html += `<p><strong>Approved:</strong> ${formatDate(externalPO.admin_approved_at)}</p>`;
    
    if (externalPO.sbc_response_status === 'PENDING') {
        html += '<div class="card-actions">';
        html += `<button onclick="sbcAcceptWork('${externalPO.id}')" class="btn-primary">Accept Work</button>`;
        html += `<button onclick="sbcRejectWork('${externalPO.id}')" class="btn-danger">Reject Work</button>`;
        html += `<button onclick="viewExternalPODetails('${externalPO.id}')">View Details</button>`;
        html += '</div>';
    } else {
        html += `<p><strong>SBC Response:</strong> <span class="badge badge-${externalPO.sbc_response_status.toLowerCase()}">${externalPO.sbc_response_status}</span></p>`;
    }
    
    html += '</div>';
    
    return html;
}

async function approveExternalPO(externalPOId) {
    const remarks = prompt('Optional remarks:');
    
    try {
        const data = await apiCall(API_ENDPOINTS.APPROVAL_RESPOND(externalPOId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'APPROVE',
                remarks: remarks
            })
        });
        
        if (data) {
            alert('External PO approved successfully!');
            loadPDApprovals();
            loadAdminApprovals();
        }
    } catch (error) {
        alert(`Failed to approve External PO: ${error.message}`);
    }
}

async function rejectExternalPO(externalPOId) {
    const rejectionReason = prompt('Please provide a rejection reason:');
    
    if (!rejectionReason) {
        return;
    }
    
    try {
        const data = await apiCall(API_ENDPOINTS.APPROVAL_RESPOND(externalPOId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'REJECT',
                rejection_reason: rejectionReason
            })
        });
        
        if (data) {
            alert('External PO rejected successfully!');
            loadPDApprovals();
            loadAdminApprovals();
        }
    } catch (error) {
        alert(`Failed to reject External PO: ${error.message}`);
    }
}

async function sbcAcceptWork(externalPOId) {
    if (!confirm('Are you sure you want to accept this work?')) {
        return;
    }
    
    try {
        const data = await apiCall(API_ENDPOINTS.SBC_RESPOND(externalPOId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'ACCEPT'
            })
        });
        
        if (data) {
            alert('Work accepted successfully!');
            loadSBCWork();
        }
    } catch (error) {
        alert(`Failed to accept work: ${error.message}`);
    }
}

async function sbcRejectWork(externalPOId) {
    const rejectionReason = prompt('Please provide a rejection reason:');
    
    if (!rejectionReason) {
        return;
    }
    
    try {
        const data = await apiCall(API_ENDPOINTS.SBC_RESPOND(externalPOId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'REJECT',
                rejection_reason: rejectionReason
            })
        });
        
        if (data) {
            alert('Work rejected successfully!');
            loadSBCWork();
        }
    } catch (error) {
        alert(`Failed to reject work: ${error.message}`);
    }
}