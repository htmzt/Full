// Enhanced Bulk Assignment Interface Functions

let selectedPOLines = [];
let allPOLinesData = []; // Store all loaded data

// Auto-load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('available-po-lines-table')) {
        loadAssignmentStats();
        loadAvailablePOLinesForAssignment(); // Auto-load on page load
    }
});

async function loadAssignmentStats() {
    const statsDiv = document.getElementById('assignment-stats');
    
    try {
        const data = await apiCall(API_ENDPOINTS.ASSIGNMENT_STATS, {
            method: 'GET'
        });
        
        if (data) {
            let html = '<div class="stats-grid">';
            html += `<div class="stat-card">
                <h3>📦 Unassigned PO Lines</h3>
                <p class="stat-number">${data.total_unassigned}</p>
            </div>`;
            html += `<div class="stat-card">
                <h3>✅ Assigned PO Lines</h3>
                <p class="stat-number">${data.total_assigned}</p>
            </div>`;
            html += `<div class="stat-card">
                <h3>🔗 With External POs</h3>
                <p class="stat-number">${data.total_with_external_po}</p>
            </div>`;
            html += `<div class="stat-card">
                <h3>⏳ Pending Approvals</h3>
                <p class="stat-number">${data.pending_assignments}</p>
            </div>`;
            html += '</div>';
            
            // Show distribution
            if (data.assignment_distribution && data.assignment_distribution.length > 0) {
                html += '<h4>Assignment Distribution</h4>';
                html += '<div style="overflow-x: auto;"><table class="stats-table"><thead><tr><th>User</th><th>Role</th><th>Assigned POs</th></tr></thead><tbody>';
                data.assignment_distribution.forEach(dist => {
                    html += `<tr>
                        <td>${dist.full_name}</td>
                        <td>${dist.role}</td>
                        <td><span class="badge">${dist.assigned_count}</span></td>
                    </tr>`;
                });
                html += '</tbody></table></div>';
            }
            
            statsDiv.innerHTML = html;
        }
    } catch (error) {
        statsDiv.innerHTML = `<div class="error">Failed to load stats: ${error.message}</div>`;
    }
}

async function loadAvailablePOLinesForAssignment(page = 1) {
    const tableDiv = document.getElementById('available-po-lines-table');
    const loadingMsg = page === 1 ? '<div class="loading">🔄 Loading PO lines...</div>' : '';
    tableDiv.innerHTML = loadingMsg;
    
    // Get filter values
    const search = document.getElementById('search-po-lines').value;
    const status = document.getElementById('filter-po-status').value;
    const category = document.getElementById('filter-po-category').value;
    const project = document.getElementById('filter-po-project').value;
    
    // Build query params
    let url = `${API_ENDPOINTS.AVAILABLE_FOR_ASSIGNMENT}?page=${page}&per_page=100`;
    
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (project) url += `&project_name=${encodeURIComponent(project)}`;
    
    try {
        const data = await apiCall(url, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            allPOLinesData = data.results; // Store for bulk operations
            
            let html = '<div class="bulk-assignment-header">';
            html += `<div class="bulk-controls">`;
            html += `<p><strong>Total Available:</strong> <span class="badge badge-primary">${data.count || data.results.length}</span> PO lines</p>`;
            html += `<p><strong>Selected:</strong> <span id="selected-count" class="badge badge-success">0</span> PO lines</p>`;
            html += `</div>`;
            html += `<div class="action-buttons">`;
            html += `<button id="assign-selected-btn" onclick="showAssignmentModal()" disabled class="btn-primary">📤 Assign Selected</button>`;
            html += `<button onclick="toggleBulkPOInput()" class="btn-secondary">📝 Bulk PO Input</button>`;
            html += `<button onclick="clearSelection()" class="btn-secondary">🗑️ Clear Selection</button>`;
            html += `</div>`;
            html += '</div>';
            
            // Bulk PO Input Section (Hidden by default)
            html += `<div id="bulk-po-input-section" style="display: none;" class="bulk-input-section">
                <h4>Bulk PO Selection</h4>
                <p>Enter PO numbers or PO IDs (one per line or comma-separated):</p>
                <textarea id="bulk-po-ids-input" rows="5" placeholder="Example:&#10;INWI-2024-001&#10;INWI-2024-002, INWI-2024-003&#10;or paste Excel column"></textarea>
                <div class="bulk-input-buttons">
                    <button onclick="selectFromBulkInput()" class="btn-primary">✓ Select These POs</button>
                    <button onclick="toggleBulkPOInput()" class="btn-secondary">Cancel</button>
                </div>
            </div>`;
            
            html += '<div style="overflow-x: auto;"><table class="po-lines-table"><thead><tr>';
            html += '<th><input type="checkbox" id="select-all-checkbox" onchange="toggleSelectAll(this)" title="Select All"></th>';
            html += '<th>PO Number</th>';
            html += '<th>Line No</th>';
            html += '<th>Project</th>';
            html += '<th>Account</th>';
            html += '<th>Description</th>';
            html += '<th>Category</th>';
            html += '<th>Amount</th>';
            html += '<th>Status</th>';
            html += '</tr></thead><tbody>';
            
            data.results.forEach(po => {
                const isChecked = selectedPOLines.some(selected => selected.po_id === po.po_id);
                html += '<tr class="' + (isChecked ? 'selected-row' : '') + '">';
                html += `<td><input type="checkbox" class="po-checkbox" 
                         value="${po.po_id}" 
                         data-po-number="${po.po_number}" 
                         data-po-line="${po.po_line_no}"
                         ${isChecked ? 'checked' : ''}
                         onchange="togglePOLineSelection(this)"></td>`;
                html += `<td><strong>${po.po_number}</strong></td>`;
                html += `<td>${po.po_line_no}</td>`;
                html += `<td>${po.project_name || 'N/A'}</td>`;
                html += `<td>${po.account_name || 'N/A'}</td>`;
                html += `<td><div class="truncate-text" title="${po.item_description || 'N/A'}">${po.item_description ? po.item_description.substring(0, 50) + '...' : 'N/A'}</div></td>`;
                html += `<td><span class="badge badge-info">${po.category || 'N/A'}</span></td>`;
                html += `<td class="amount">${formatCurrency(po.line_amount)}</td>`;
                html += `<td><span class="badge badge-${getStatusBadgeClass(po.status)}">${po.status || 'N/A'}</span></td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table></div>';
            tableDiv.innerHTML = html;
            
            // Update selected count
            updateSelectedCount();
            
            // Render pagination if needed
            if (data.count > 100) {
                renderAssignmentPagination(data.count, page);
            }
        } else {
            tableDiv.innerHTML = '<div class="empty-state"><p>📭 No unassigned PO lines found</p><p>Try adjusting your search filters</p></div>';
        }
    } catch (error) {
        tableDiv.innerHTML = `<div class="error">❌ Failed to load PO lines: ${error.message}</div>`;
    }
}

function toggleSelectAll(checkbox) {
    const allCheckboxes = document.querySelectorAll('.po-checkbox');
    allCheckboxes.forEach(cb => {
        cb.checked = checkbox.checked;
        togglePOLineSelection(cb);
    });
}

function togglePOLineSelection(checkbox) {
    const poId = checkbox.value;
    const poNumber = checkbox.dataset.poNumber;
    const poLine = checkbox.dataset.poLine;
    const row = checkbox.closest('tr');
    
    if (checkbox.checked) {
        // Add to selection if not already there
        if (!selectedPOLines.some(po => po.po_id === poId)) {
            selectedPOLines.push({
                po_id: poId,
                po_number: poNumber,
                po_line: poLine
            });
        }
        row.classList.add('selected-row');
    } else {
        // Remove from selection
        selectedPOLines = selectedPOLines.filter(po => po.po_id !== poId);
        row.classList.remove('selected-row');
    }
    
    updateSelectedCount();
}

function updateSelectedCount() {
    const countSpan = document.getElementById('selected-count');
    const assignBtn = document.getElementById('assign-selected-btn');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    
    if (countSpan) {
        countSpan.textContent = selectedPOLines.length;
    }
    
    if (assignBtn) {
        assignBtn.disabled = selectedPOLines.length === 0;
    }
    
    // Update select all checkbox state
    if (selectAllCheckbox) {
        const allCheckboxes = document.querySelectorAll('.po-checkbox');
        const checkedBoxes = document.querySelectorAll('.po-checkbox:checked');
        selectAllCheckbox.checked = allCheckboxes.length > 0 && allCheckboxes.length === checkedBoxes.length;
        selectAllCheckbox.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < allCheckboxes.length;
    }
}

function clearSelection() {
    selectedPOLines = [];
    const allCheckboxes = document.querySelectorAll('.po-checkbox');
    allCheckboxes.forEach(cb => {
        cb.checked = false;
        const row = cb.closest('tr');
        if (row) row.classList.remove('selected-row');
    });
    updateSelectedCount();
}

function toggleBulkPOInput() {
    const section = document.getElementById('bulk-po-input-section');
    if (section.style.display === 'none') {
        section.style.display = 'block';
    } else {
        section.style.display = 'none';
        document.getElementById('bulk-po-ids-input').value = '';
    }
}

function selectFromBulkInput() {
    const input = document.getElementById('bulk-po-ids-input').value;
    if (!input.trim()) {
        alert('Please enter PO numbers or IDs');
        return;
    }
    
    // Parse input - handle newlines, commas, and whitespace
    const poIdentifiers = input
        .split(/[\n,]+/)
        .map(id => id.trim())
        .filter(id => id.length > 0);
    
    if (poIdentifiers.length === 0) {
        alert('No valid PO identifiers found');
        return;
    }
    
    let matchedCount = 0;
    let notFoundList = [];
    
    // Check each PO in the current loaded data
    poIdentifiers.forEach(identifier => {
        const found = allPOLinesData.find(po => 
            po.po_number === identifier || 
            po.po_id === identifier ||
            po.po_number.includes(identifier)
        );
        
        if (found) {
            // Check if not already selected
            if (!selectedPOLines.some(selected => selected.po_id === found.po_id)) {
                selectedPOLines.push({
                    po_id: found.po_id,
                    po_number: found.po_number,
                    po_line: found.po_line_no
                });
                
                // Check the checkbox in the UI
                const checkbox = document.querySelector(`.po-checkbox[value="${found.po_id}"]`);
                if (checkbox) {
                    checkbox.checked = true;
                    const row = checkbox.closest('tr');
                    if (row) row.classList.add('selected-row');
                }
                matchedCount++;
            }
        } else {
            notFoundList.push(identifier);
        }
    });
    
    // Show results
    let message = `✓ Selected ${matchedCount} PO line(s)`;
    if (notFoundList.length > 0) {
        message += `\n\n⚠️ Not found or not available (${notFoundList.length}):\n${notFoundList.join('\n')}`;
        message += '\n\nNote: POs might be already assigned or not in current filter results.';
    }
    
    alert(message);
    
    // Update UI
    updateSelectedCount();
    toggleBulkPOInput();
}

async function loadAssignableUsers() {
    try {
        const data = await apiCall(API_ENDPOINTS.ASSIGNABLE_USERS, {
            method: 'GET'
        });
        
        if (data && data.results) {
            const select = document.getElementById('bulk-assign-user');
            select.innerHTML = '<option value="">Select User...</option>';
            
            data.results.forEach(user => {
                const assignedInfo = user.current_assignment_count > 0 
                    ? ` (${user.current_assignment_count} assigned)` 
                    : '';
                select.innerHTML += `<option value="${user.id}">${user.full_name} - ${user.role_display}${assignedInfo}</option>`;
            });
        }
    } catch (error) {
        console.error('Failed to load assignable users:', error);
    }
}

function showAssignmentModal() {
    if (selectedPOLines.length === 0) {
        alert('Please select at least one PO line');
        return;
    }
    
    const modal = document.getElementById('assignment-modal');
    const modalContent = document.getElementById('assignment-modal-content');
    
    // Calculate total amount of selected POs
    let totalAmount = 0;
    selectedPOLines.forEach(selected => {
        const poData = allPOLinesData.find(po => po.po_id === selected.po_id);
        if (poData && poData.line_amount) {
            totalAmount += parseFloat(poData.line_amount);
        }
    });
    
    modalContent.innerHTML = `
        <h3>📤 Assign ${selectedPOLines.length} PO Line(s)</h3>
        <p class="modal-summary">Total Amount: <strong>${formatCurrency(totalAmount)}</strong></p>
        <form id="bulk-assignment-form" onsubmit="executeBulkAssignment(event)">
            <div class="form-group">
                <label>Assign to: <span class="required">*</span></label>
                <select id="bulk-assign-user" required>
                    <option value="">Loading users...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Assignment Notes:</label>
                <textarea id="bulk-assign-notes" rows="4" placeholder="Optional notes for the assigned user..."></textarea>
            </div>
            <div class="form-group">
                <strong>Selected PO Lines:</strong>
                <div class="selected-po-list">
                    ${selectedPOLines.map(po => `<div class="po-item">✓ ${po.po_number}-${po.po_line}</div>`).join('')}
                </div>
            </div>
            <div class="modal-actions">
                <button type="submit" class="btn-primary">✓ Confirm Assignment</button>
                <button type="button" onclick="closeAssignmentModal()" class="btn-secondary">Cancel</button>
            </div>
        </form>
    `;
    
    modal.style.display = 'flex';
    
    // Load users
    loadAssignableUsers();
}

function closeAssignmentModal() {
    const modal = document.getElementById('assignment-modal');
    modal.style.display = 'none';
}

async function executeBulkAssignment(event) {
    event.preventDefault();
    
    const userId = document.getElementById('bulk-assign-user').value;
    const notes = document.getElementById('bulk-assign-notes').value;
    
    if (!userId) {
        alert('Please select a user');
        return;
    }
    
    if (selectedPOLines.length === 0) {
        alert('No PO lines selected');
        return;
    }
    
    // Disable submit button
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Assigning...';
    
    try {
        const payload = {
            po_ids: selectedPOLines.map(po => po.po_id),
            assigned_to: userId,
            notes: notes
        };
        
        const response = await apiCall(API_ENDPOINTS.CREATE_ASSIGNMENT, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        
        if (response) {
            alert(`✓ Successfully assigned ${selectedPOLines.length} PO line(s)!`);
            closeAssignmentModal();
            
            // Clear selection and reload data
            clearSelection();
            loadAssignmentStats();
            loadAvailablePOLinesForAssignment();
        }
    } catch (error) {
        alert(`❌ Assignment failed: ${error.message}`);
        submitBtn.disabled = false;
        submitBtn.textContent = '✓ Confirm Assignment';
    }
}

function renderAssignmentPagination(totalCount, currentPage) {
    const paginationDiv = document.getElementById('assignment-pagination');
    if (!paginationDiv) return;
    
    const perPage = 100;
    const totalPages = Math.ceil(totalCount / perPage);
    
    let html = '<div class="pagination">';
    
    // Previous button
    if (currentPage > 1) {
        html += `<button onclick="loadAvailablePOLinesForAssignment(${currentPage - 1})">« Previous</button>`;
    }
    
    // Page numbers
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
        const active = i === currentPage ? 'active' : '';
        html += `<button class="${active}" onclick="loadAvailablePOLinesForAssignment(${i})">${i}</button>`;
    }
    
    if (totalPages > 5) {
        html += '<span>...</span>';
        html += `<button onclick="loadAvailablePOLinesForAssignment(${totalPages})">${totalPages}</button>`;
    }
    
    // Next button
    if (currentPage < totalPages) {
        html += `<button onclick="loadAvailablePOLinesForAssignment(${currentPage + 1})">Next »</button>`;
    }
    
    html += `<span class="page-info">Page ${currentPage} of ${totalPages} (${totalCount} total)</span>`;
    html += '</div>';
    
    paginationDiv.innerHTML = html;
}

// Helper function for currency formatting
function formatCurrency(amount) {
    if (!amount && amount !== 0) return 'N/A';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

// Helper function for status badge classes
function getStatusBadgeClass(status) {
    if (!status) return 'secondary';
    
    const statusLower = status.toLowerCase();
    if (statusLower.includes('closed') || statusLower.includes('completed')) return 'success';
    if (statusLower.includes('pending')) return 'warning';
    if (statusLower.includes('cancelled') || statusLower.includes('rejected')) return 'danger';
    return 'info';
}