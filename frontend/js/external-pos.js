// External PO functions

let selectedPOLines = [];

async function loadSBCUsers() {
    try {
        const data = await apiCall(API_ENDPOINTS.USERS, {
            method: 'GET'
        });
        
        if (data && data.results) {
            const select = document.getElementById('external-po-sbc');
            select.innerHTML = '<option value="">Select SBC...</option>';
            
            // Filter SBC users
            data.results
                .filter(user => user.role === 'SBC')
                .forEach(user => {
                    select.innerHTML += `<option value="${user.id}">${user.full_name} - ${user.sbc_company_name || ''}</option>`;
                });
        }
    } catch (error) {
        console.error('Failed to load SBC users:', error);
    }
}

async function loadAvailablePOLines() {
    const listDiv = document.getElementById('available-po-lines');
    listDiv.innerHTML = '<div class="loading"></div> Loading available PO lines...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.AVAILABLE_PO_LINES, {
            method: 'GET'
        });
        
        if (data && data.length > 0) {
            let html = '<div class="checkbox-list">';
            html += '<p><strong>Select PO Lines:</strong></p>';
            
            data.forEach((po, index) => {
                html += `<div class="checkbox-item">`;
                html += `<label>`;
                html += `<input type="checkbox" value="${po.po_id}" data-po-number="${po.po_number}" data-po-line="${po.po_line_no}" onchange="togglePOLine(this)">`;
                html += `${po.po_number}-${po.po_line_no} | ${po.project_name || 'N/A'} | ${formatCurrency(po.line_amount)} | ${po.status}`;
                html += `</label>`;
                html += `</div>`;
            });
            
            html += '</div>';
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="empty-state"><p>No available PO lines found</p></div>';
        }
    } catch (error) {
        listDiv.innerHTML = `<div class="error">Failed to load PO lines: ${error.message}</div>`;
    }
}

function togglePOLine(checkbox) {
    const poId = checkbox.value;
    const poNumber = checkbox.dataset.poNumber;
    const poLine = checkbox.dataset.poLine;
    
    if (checkbox.checked) {
        selectedPOLines.push({
            po_id: poId,
            po_number: poNumber,
            po_line: poLine
        });
    } else {
        selectedPOLines = selectedPOLines.filter(po => po.po_id !== poId);
    }
}

async function createExternalPO(event) {
    event.preventDefault();
    
    if (selectedPOLines.length === 0) {
        alert('Please select at least one PO line');
        return;
    }
    
    const sbcId = document.getElementById('external-po-sbc').value;
    const notes = document.getElementById('external-po-notes').value;
    const internalNotes = document.getElementById('external-po-internal-notes').value;
    const saveAsDraft = document.getElementById('external-po-draft').checked;
    
    const resultDiv = document.getElementById('external-po-create-result');
    resultDiv.innerHTML = '<div class="loading"></div> Creating External PO...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.CREATE_EXTERNAL_PO, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                po_lines: selectedPOLines,
                assigned_to_sbc_id: sbcId,
                assignment_notes: notes,
                internal_notes: internalNotes,
                save_as_draft: saveAsDraft
            })
        });
        
        if (data) {
            resultDiv.innerHTML = `
                <div class="success">
                    <h4>✅ External PO Created!</h4>
                    <p><strong>Internal PO ID:</strong> ${data.internal_po_id}</p>
                    <p><strong>Status:</strong> ${data.status}</p>
                    <p><strong>PO Line Count:</strong> ${data.po_line_count}</p>
                    <p><strong>Estimated Amount:</strong> ${formatCurrency(data.estimated_total_amount)}</p>
                </div>
            `;
            
            // Clear form and selections
            document.getElementById('create-external-po-form').reset();
            selectedPOLines = [];
            loadAvailablePOLines();
            loadExternalPOs();
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Failed to create External PO: ${error.message}</div>`;
    }
}

async function loadExternalPOs() {
    const listDiv = document.getElementById('external-pos-list');
    listDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.EXTERNAL_POS, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '';
            data.results.forEach(externalPO => {
                html += renderExternalPOCard(externalPO);
            });
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="empty-state"><p>No External POs found</p></div>';
        }
    } catch (error) {
        listDiv.innerHTML = `<div class="error">Failed to load External POs: ${error.message}</div>`;
    }
}

function renderExternalPOCard(externalPO) {
    let html = '<div class="card">';
    html += `<h4>${externalPO.internal_po_id}</h4>`;
    html += `<p><strong>Status:</strong> <span class="badge badge-${getStatusBadgeClass(externalPO.status)}">${externalPO.status}</span></p>`;
    html += `<p><strong>PO Line Count:</strong> ${externalPO.po_line_count}</p>`;
    html += `<p><strong>Assigned to SBC:</strong> ${externalPO.assigned_to_sbc_name}</p>`;
    html += `<p><strong>Estimated Amount:</strong> ${formatCurrency(externalPO.estimated_total_amount)}</p>`;
    html += `<p><strong>Created:</strong> ${formatDate(externalPO.created_at)}</p>`;
    
    if (externalPO.submitted_at) {
        html += `<p><strong>Submitted:</strong> ${formatDate(externalPO.submitted_at)}</p>`;
    }
    
    html += '<div class="card-actions">';
    
    if (externalPO.status === 'DRAFT') {
        html += `<button onclick="submitExternalPO('${externalPO.id}')" class="btn-primary">Submit for Approval</button>`;
        html += `<button onclick="deleteExternalPO('${externalPO.id}')" class="btn-danger">Delete</button>`;
    }
    
    html += `<button onclick="viewExternalPODetails('${externalPO.id}')">View Details</button>`;
    html += '</div>';
    html += '</div>';
    
    return html;
}

async function submitExternalPO(externalPOId) {
    if (!confirm('Are you sure you want to submit this External PO for approval?')) {
        return;
    }
    
    try {
        const data = await apiCall(API_ENDPOINTS.EXTERNAL_PO_SUBMIT(externalPOId), {
            method: 'POST'
        });
        
        if (data) {
            alert('External PO submitted successfully!');
            loadExternalPOs();
        }
    } catch (error) {
        alert(`Failed to submit External PO: ${error.message}`);
    }
}

async function deleteExternalPO(externalPOId) {
    if (!confirm('Are you sure you want to delete this External PO?')) {
        return;
    }
    
    try {
        await apiCall(API_ENDPOINTS.EXTERNAL_PO_DELETE(externalPOId), {
            method: 'DELETE'
        });
        
        alert('External PO deleted successfully!');
        loadExternalPOs();
    } catch (error) {
        alert(`Failed to delete External PO: ${error.message}`);
    }
}

async function viewExternalPODetails(externalPOId) {
    try {
        const data = await apiCall(API_ENDPOINTS.EXTERNAL_PO_DETAIL(externalPOId), {
            method: 'GET'
        });
        
        if (data) {
            let details = `
                Internal PO ID: ${data.internal_po_id}
                Status: ${data.status}
                PO Numbers: ${data.po_numbers.join(', ')}
                PO Line Count: ${data.po_line_count}
                Assigned to SBC: ${data.assigned_to_sbc_name} (${data.assigned_to_sbc_company})
                Estimated Amount: ${formatCurrency(data.estimated_total_amount)}
                Created By: ${data.created_by_name}
                Created At: ${formatDate(data.created_at)}
                
                ${data.assignment_notes ? 'Assignment Notes:\n' + data.assignment_notes : ''}
                ${data.internal_notes ? '\n\nInternal Notes:\n' + data.internal_notes : ''}
                
                ${data.pd_approved_by_name ? '\nPD Approved By: ' + data.pd_approved_by_name : ''}
                ${data.pd_approved_at ? 'PD Approved At: ' + formatDate(data.pd_approved_at) : ''}
                
                ${data.admin_approved_by_name ? '\nAdmin Approved By: ' + data.admin_approved_by_name : ''}
                ${data.admin_approved_at ? 'Admin Approved At: ' + formatDate(data.admin_approved_at) : ''}
                
                ${data.rejection_reason ? '\nRejection Reason: ' + data.rejection_reason : ''}
                ${data.rejected_by_name ? 'Rejected By: ' + data.rejected_by_name : ''}
            `;
            
            alert(details);
        }
    } catch (error) {
        alert(`Failed to load External PO details: ${error.message}`);
    }
}

// Load SBC users when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadSBCUsers();
});