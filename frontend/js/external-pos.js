// External PO functions

let externalSelectedPOLines = []; // Renamed to avoid conflict

async function loadSBCUsers() {
    // Unchanged
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
    const poNumber = checkbox.getAttribute('data-po-number');
    const poLine = checkbox.getAttribute('data-po-line');
    
    if (checkbox.checked) {
        if (!externalSelectedPOLines.some(po => po.po_id === poId)) {
            externalSelectedPOLines.push({ po_id: poId, po_number: poNumber, po_line: poLine });
        }
    } else {
        externalSelectedPOLines = externalSelectedPOLines.filter(po => po.po_id !== poId);
    }
}

// ... rest of the file unchanged ...

document.addEventListener('DOMContentLoaded', () => {
    loadSBCUsers();
});