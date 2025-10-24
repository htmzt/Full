// Bulk Assignment Interface Functions

let selectedPOLines = [];

async function loadAssignmentStats() {
    const statsDiv = document.getElementById('assignment-stats');
    
    try {
        const data = await apiCall(API_ENDPOINTS.ASSIGNMENT_STATS, {
            method: 'GET'
        });
        
        if (data) {
            let html = '<div class="stats-grid">';
            html += `<div class="stat-card">
                <h3>Unassigned PO Lines</h3>
                <p>${data.total_unassigned}</p>
            </div>`;
            html += `<div class="stat-card">
                <h3>Assigned PO Lines</h3>
                <p>${data.total_assigned}</p>
            </div>`;
            html += `<div class="stat-card">
                <h3>With External POs</h3>
                <p>${data.total_with_external_po}</p>
            </div>`;
            html += `<div class="stat-card">
                <h3>Pending Approvals</h3>
                <p>${data.pending_assignments}</p>
            </div>`;
            html += '</div>';
            
            // Show distribution
            if (data.assignment_distribution && data.assignment_distribution.length > 0) {
                html += '<h4>Assignment Distribution</h4>';
                html += '<table><thead><tr><th>User</th><th>Role</th><th>Assigned POs</th></tr></thead><tbody>';
                data.assignment_distribution.forEach(dist => {
                    html += `<tr>
                        <td>${dist.full_name}</td>
                        <td>${dist.role}</td>
                        <td>${dist.assigned_count}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
            }
            
            statsDiv.innerHTML = html;
        }
    } catch (error) {
        statsDiv.innerHTML = `<div class="error">Failed to load stats: ${error.message}</div>`;
    }
}

async function loadAvailablePOLinesForAssignment(page = 1) {
    const tableDiv = document.getElementById('available-po-lines-table');
    tableDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    // Get filter values
    const search = document.getElementById('search-po-lines').value;
    const status = document.getElementById('filter-po-status').value;
    const category = document.getElementById('filter-po-category').value;
    const project = document.getElementById('filter-po-project').value;
    
    // Build query params
    let url = `${API_ENDPOINTS.AVAILABLE_FOR_ASSIGNMENT}?page=${page}&per_page=50`;
    
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (project) url += `&project_name=${encodeURIComponent(project)}`;
    
    try {
        const data = await apiCall(url, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '<div class="bulk-assignment-controls">';
            html += `<p><strong>Selected:</strong> <span id="selected-count">0</span> PO lines</p>`;
            html += '<button id="assign-selected-btn" onclick="showAssignmentModal()" disabled>Assign Selected</button>';
            html += '</div>';
            
            html += '<div style="overflow-x: auto;"><table><thead><tr>';
            html += '<th><input type="checkbox" id="select-all-checkbox" onchange="toggleSelectAll(this)"></th>';
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
                html += '<tr>';
                html += `<td><input type="checkbox" class="po-checkbox" 
                         value="${po.po_id}" 
                         data-po-number="${po.po_number}" 
                         data-po-line="${po.po_line_no}"
                         ${isChecked ? 'checked' : ''}
                         onchange="togglePOLineSelection(this)"></td>`;
                html += `<td>${po.po_number}</td>`;
                html += `<td>${po.po_line_no}</td>`;
                html += `<td>${po.project_name || 'N/A'}</td>`;
                html += `<td>${po.account_name || 'N/A'}</td>`;
                html += `<td title="${po.item_description || 'N/A'}">${po.item_description ? po.item_description.substring(0, 40) + '...' : 'N/A'}</td>`;
                html += `<td>${po.category || 'N/A'}</td>`;
                html += `<td>${formatCurrency(po.line_amount)}</td>`;
                html += `<td><span class="badge badge-${getStatusBadgeClass(po.status)}">${po.status || 'N/A'}</span></td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table></div>';
            tableDiv.innerHTML = html;
            
            // Update selected count
            updateSelectedCount();
            
            // Render pagination if needed
            if (data.count > 50) {
                renderAssignmentPagination(data.count, page);
            }
        } else {
            tableDiv.innerHTML = '<div class="empty-state"><p>No unassigned PO lines found</p></div>';
        }
    } catch (error) {
        tableDiv.innerHTML = `<div class="error">Failed to load PO lines: ${error.message}</div>`;
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
    
    if (checkbox.checked) {
        // Add to selection if not already there
        if (!selectedPOLines.some(po => po.po_id === poId)) {
            selectedPOLines.push({
                po_id: poId,
                po_number: poNumber,
                po_line: poLine
            });
        }
    } else {
        // Remove from selection
        selectedPOLines = selectedPOLines.filter(po => po.po_id !== poId);
    }
    
    updateSelectedCount();
}

function updateSelectedCount() {
    const countSpan = document.getElementById('selected-count');
    const assignBtn = document.getElementById('assign-selected-btn');
    
    if (countSpan) {
        countSpan.textContent = selectedPOLines.length;
    }
    
    if (assignBtn) {
        assignBtn.disabled = selectedPOLines.length === 0;
    }
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
    
    modalContent.innerHTML = `
        <h3>Assign ${selectedPOLines.length} PO Line(s)</h3>
        <form id="bulk-assignment-form" onsubmit="executeBulkAssignment(event)">
            <div class="form-group">
                <label>Assign to:</label>
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
                    ${selectedPOLines.map(po => `<div>${po.po_number}-${po.po_line}</div>`).join('')}
                </div>
            </div>
            <div class="modal-actions">
                <button type="button" onclick="closeAssignmentModal()">Cancel</button>
                <button type="submit" class="btn-primary">Create Assignment</button>
            </div>
        </form>
        <div id="bulk-assignment-result"></div>
    `;
    
    modal.style.display = 'block';
    
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
    const resultDiv = document.getElementById('bulk-assignment-result');
    
    if (!userId) {
        resultDiv.innerHTML = '<div class="error">Please select a user</div>';
        return;
    }
    
    resultDiv.innerHTML = '<div class="loading"></div> Creating assignment...';
    
    // Extract just the po_id values
    const poIds = selectedPOLines.map(po => po.po_id);
    
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
                    <h4>✅ Assignment Created Successfully!</h4>
                    <p><strong>Assignment ID:</strong> ${data.id}</p>
                    <p><strong>PO Lines:</strong> ${data.po_count}</p>
                    <p><strong>Assigned To:</strong> ${data.assigned_to_name}</p>
                    <p><strong>Status:</strong> ${data.status}</p>
                </div>
            `;
            
            // Clear selection
            selectedPOLines = [];
            
            // Reload data
            setTimeout(() => {
                closeAssignmentModal();
                loadAvailablePOLinesForAssignment();
                loadAssignmentStats();
            }, 2000);
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Failed to create assignment: ${error.message}</div>`;
    }
}

function renderAssignmentPagination(totalCount, currentPage) {
    const paginationDiv = document.getElementById('assignment-pagination');
    const perPage = 50;
    const totalPages = Math.ceil(totalCount / perPage);
    
    if (totalPages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }
    
    let html = '<div class="pagination">';
    
    // Previous button
    if (currentPage > 1) {
        html += `<button onclick="loadAvailablePOLinesForAssignment(${currentPage - 1})">Previous</button>`;
    }
    
    // Page numbers
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        html += `<button class="${activeClass}" onclick="loadAvailablePOLinesForAssignment(${i})">${i}</button>`;
    }
    
    // Next button
    if (currentPage < totalPages) {
        html += `<button onclick="loadAvailablePOLinesForAssignment(${currentPage + 1})">Next</button>`;
    }
    
    html += `</div><p style="text-align: center; margin-top: 10px;">Page ${currentPage} of ${totalPages} (${totalCount} total PO lines)</p>`;
    paginationDiv.innerHTML = html;
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('assignment-modal');
    if (event.target === modal) {
        closeAssignmentModal();
    }
}