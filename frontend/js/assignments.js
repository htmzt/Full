// ============================================================================
// UNIFIED ASSIGNMENT SYSTEM
// Clean flow: View merged data → Select rows → Assign to users
// ============================================================================

let selectedPOLines = [];
let allPOLinesData = [];
let currentPage = 1;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('showSection', (event) => {
    if (event.detail === 'assignments') {
        console.log('Assignment section activated');
        const user = getUserData();
        if (user && user.can_assign_pos) {
            loadAssignmentStats();
            loadAvailablePOLinesForAssignment();
            loadAssignableUsers();
        }
        loadMyAssignments();
        loadCreatedAssignments();

        // Attach event listeners for filter and reset buttons
        const applyFiltersBtn = document.getElementById('apply-filters-btn');
        const resetFiltersBtn = document.getElementById('reset-filters-btn');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => loadAvailablePOLinesForAssignment(1));
        }
        if (resetFiltersBtn) {
            resetFiltersBtn.addEventListener('click', resetFilters);
        }

        // Attach event listeners for filter inputs
        const filterInputs = [
            document.getElementById('search-po-lines'),
            document.getElementById('filter-po-status'),
            document.getElementById('filter-po-category'),
            document.getElementById('filter-po-project')
        ];
        filterInputs.forEach(input => {
            if (input) {
                input.addEventListener('change', () => loadAvailablePOLinesForAssignment(1));
            }
        });
    }
});

// ============================================================================
// SECTION: ASSIGNMENT STATISTICS
// ============================================================================

async function loadAssignmentStats() {
    const statsDiv = document.getElementById('assignment-stats');
    if (!statsDiv) {
        console.error('Stats div not found!');
        return;
    }
    
    statsDiv.innerHTML = '<div class="loading">Loading stats...</div>';
    
    try {
        const data = await apiCall(API_ENDPOINTS.ASSIGNMENT_STATS, {
            method: 'GET'
        });
        
        console.log('Assignment stats:', data);
        
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
            
            if (data.assignment_distribution && data.assignment_distribution.length > 0) {
                html += '<div style="margin-top: 20px;">';
                html += '<h4>📊 Assignment Distribution by User</h4>';
                html += '<div style="overflow-x: auto;"><table class="stats-table">';
                html += '<thead><tr><th>User</th><th>Role</th><th>Assigned POs</th></tr></thead><tbody>';
                
                data.assignment_distribution.forEach(dist => {
                    html += `<tr>
                        <td>${escapeHtml(dist.full_name)}</td>
                        <td><span class="badge badge-info">${escapeHtml(dist.role)}</span></td>
                        <td><span class="badge badge-success">${dist.assigned_count}</span></td>
                    </tr>`;
                });
                
                html += '</tbody></table></div></div>';
            }
            
            statsDiv.innerHTML = html;
        } else {
            statsDiv.innerHTML = '<div class="error">No stats data received</div>';
        }
    } catch (error) {
        console.error('Failed to load assignment stats:', error);
        statsDiv.innerHTML = `<div class="error">❌ Failed to load stats: ${error.message}</div>`;
    }
}

// ============================================================================
// SECTION: AVAILABLE PO LINES
// ============================================================================

async function loadAvailablePOLinesForAssignment(page = 1) {
    const tableDiv = document.getElementById('available-po-lines-table');
    if (!tableDiv) {
        console.error('Table div not found!');
        return;
    }
    
    tableDiv.innerHTML = '<div class="loading">🔄 Loading available PO lines...</div>';
    
    currentPage = page;
    
    const searchInput = document.getElementById('search-po-lines');
    const statusSelect = document.getElementById('filter-po-status');
    const categorySelect = document.getElementById('filter-po-category');
    const projectInput = document.getElementById('filter-po-project');
    
    const search = searchInput ? searchInput.value : '';
    const status = statusSelect ? statusSelect.value : '';
    const category = categorySelect ? categorySelect.value : '';
    const project = projectInput ? projectInput.value : '';
    
    let url = `${API_ENDPOINTS.AVAILABLE_FOR_ASSIGNMENT}?page=${page}&per_page=100`;
    
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (project) url += `&project_name=${encodeURIComponent(project)}`;
    
    try {
        const data = await apiCall(url, {
            method: 'GET'
        });
        
        console.log('Available PO lines:', data);
        
        if (data && data.results && data.results.length > 0) {
            allPOLinesData = data.results;
            
            let html = '<div class="assignment-control-bar">';
            html += '<div>';
            html += '<input type="text" id="search-po-lines" placeholder="Search PO number, description..." value="' + escapeHtml(search) + '">';
            html += '<select id="filter-po-status"><option value="">All Statuses</option><option value="Open">Open</option><option value="Closed">Closed</option></select>';
            html += '<select id="filter-po-category"><option value="">All Categories</option><option value="Materials">Materials</option><option value="Services">Services</option></select>';
            html += '<input type="text" id="filter-po-project" placeholder="Project name..." value="' + escapeHtml(project) + '">';
            html += '<button id="apply-filters-btn">Apply Filters</button>';
            html += '<button id="reset-filters-btn">Reset Filters</button>';
            html += '<button id="assign-selected-btn" onclick="showAssignmentModal()" disabled>Assign Selected</button>';
            html += '</div>';
            html += `<p><strong>Total Available:</strong> <span class="badge badge-primary">${data.count}</span> PO lines</p>`;
            html += `<p><strong>Selected:</strong> <span id="selected-count" class="badge badge-success">${selectedPOLines.length}</span> PO lines</p>`;
            html += '</div>';
            
            html += '<table class="po-lines-table">';
            html += '<thead><tr><th><input type="checkbox" id="select-all-pos" onclick="toggleSelectAll()"></th><th>PO Number</th><th>Line</th><th>Project</th><th>Account</th><th>Description</th><th>Category</th><th>Amount</th><th>Status</th></tr></thead>';
            html += '<tbody>';
            
            data.results.forEach(po => {
                const isSelected = selectedPOLines.some(selected => selected.po_id === po.po_id);
                const rowClass = isSelected ? 'selected-row' : '';
                const isSelectable = !po.is_assigned && !po.has_external_po;
                
                html += `<tr class="${rowClass}">`;
                html += `<td><input type="checkbox" class="po-checkbox" data-po-id="${po.po_id}" data-po-number="${escapeHtml(po.po_number)}" data-po-line="${escapeHtml(po.po_line_no)}" ${isSelected ? 'checked' : ''} ${isSelectable ? '' : 'disabled'} onclick="togglePOSelection(this)"></td>`;
                html += `<td>${escapeHtml(po.po_number)}</td>`;
                html += `<td>${escapeHtml(po.po_line_no)}</td>`;
                html += `<td>${escapeHtml(po.project_name || 'N/A')}</td>`;
                html += `<td>${escapeHtml(po.account_name || 'N/A')}</td>`;
                html += `<td>${escapeHtml(po.item_description || 'N/A')}</td>`;
                html += `<td>${escapeHtml(po.category || 'N/A')}</td>`;
                html += `<td>${formatCurrency(po.line_amount)}</td>`;
                html += `<td><span class="badge badge-${getStatusBadgeClass(po.status)}">${escapeHtml(po.status || 'N/A')}</span></td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            
            tableDiv.innerHTML = html;
            renderAssignmentPagination(data.count, page);
            updateAssignButtonState();
            
            // Reattach filter event listeners
            const newSearchInput = document.getElementById('search-po-lines');
            const newStatusSelect = document.getElementById('filter-po-status');
            const newCategorySelect = document.getElementById('filter-po-category');
            const newProjectInput = document.getElementById('filter-po-project');
            const newApplyFiltersBtn = document.getElementById('apply-filters-btn');
            const newResetFiltersBtn = document.getElementById('reset-filters-btn');
            const filterInputs = [newSearchInput, newStatusSelect, newCategorySelect, newProjectInput];
            filterInputs.forEach(input => {
                if (input) {
                    input.addEventListener('change', () => loadAvailablePOLinesForAssignment(1));
                }
            });
            if (newApplyFiltersBtn) {
                newApplyFiltersBtn.addEventListener('click', () => loadAvailablePOLinesForAssignment(1));
            }
            if (newResetFiltersBtn) {
                newResetFiltersBtn.addEventListener('click', resetFilters);
            }
        } else {
            tableDiv.innerHTML = '<div class="empty-state"><p>No unassigned PO lines found</p></div>';
        }
    } catch (error) {
        console.error('Failed to load PO lines:', error);
        tableDiv.innerHTML = `<div class="error">❌ Failed to load PO lines: ${error.message}</div>`;
    }
}

// ============================================================================
// SECTION: SELECTION HANDLING
// ============================================================================

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('select-all-pos');
    const checkboxes = document.querySelectorAll('.po-checkbox:not(:disabled)');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
        togglePOSelection(checkbox);
    });
    
    updateAssignButtonState();
}

function togglePOSelection(checkbox) {
    const poId = checkbox.getAttribute('data-po-id');
    const poNumber = checkbox.getAttribute('data-po-number');
    const poLine = checkbox.getAttribute('data-po-line');
    
    if (checkbox.checked) {
        if (!selectedPOLines.some(po => po.po_id === poId)) {
            selectedPOLines.push({ po_id: poId, po_number: poNumber, po_line: poLine });
            checkbox.closest('tr').classList.add('selected-row');
        }
    } else {
        selectedPOLines = selectedPOLines.filter(po => po.po_id !== poId);
        checkbox.closest('tr').classList.remove('selected-row');
    }
    
    const selectedCount = document.getElementById('selected-count');
    if (selectedCount) {
        selectedCount.textContent = selectedPOLines.length;
    }
    
    updateAssignButtonState();
}

function updateAssignButtonState() {
    const assignButton = document.getElementById('assign-selected-btn');
    if (assignButton) {
        assignButton.disabled = selectedPOLines.length === 0;
    }
}

function resetFilters() {
    const searchInput = document.getElementById('search-po-lines');
    const statusSelect = document.getElementById('filter-po-status');
    const categorySelect = document.getElementById('filter-po-category');
    const projectInput = document.getElementById('filter-po-project');
    
    if (searchInput) searchInput.value = '';
    if (statusSelect) statusSelect.value = '';
    if (categorySelect) categorySelect.value = '';
    if (projectInput) projectInput.value = '';
    
    loadAvailablePOLinesForAssignment(1);
}

function clearSelection() {
    selectedPOLines = [];
    const checkboxes = document.querySelectorAll('.po-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
        checkbox.closest('tr').classList.remove('selected-row');
    });
    
    const selectedCount = document.getElementById('selected-count');
    if (selectedCount) {
        selectedCount.textContent = '0';
    }
    
    const selectAllCheckbox = document.getElementById('select-all-pos');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = false;
    }
    
    updateAssignButtonState();
}

// ============================================================================
// SECTION: ASSIGNMENT MODAL
// ============================================================================

async function loadAssignableUsers() {
    const userSelect = document.getElementById('bulk-assign-user');
    if (!userSelect) return;
    
    try {
        const users = await apiCall(API_ENDPOINTS.ASSIGNABLE_USERS, {
            method: 'GET'
        });
        
        console.log('Assignable users:', users);
        
        let html = '<option value="">Select User</option>';
        if (users && users.length > 0) {
            users.forEach(user => {
                html += `<option value="${user.id}">${escapeHtml(user.full_name)} (${user.role_display}, ${user.current_assignment_count} assigned)</option>`;
            });
        }
        userSelect.innerHTML = html;
    } catch (error) {
        console.error('Failed to load assignable users:', error);
        userSelect.innerHTML = '<option value="">Error loading users</option>';
    }
}

function showAssignmentModal() {
    const modal = document.getElementById('assignment-modal');
    const modalContent = document.getElementById('assignment-modal-content');
    if (!modal || !modalContent) return;
    
    modalContent.innerHTML = `
        <form onsubmit="executeBulkAssignment(event)">
            <h3>Assign ${selectedPOLines.length} PO Line(s)</h3>
            <div class="form-group">
                <label for="bulk-assign-user">Assign to:</label>
                <select id="bulk-assign-user" required></select>
            </div>
            <div class="form-group">
                <label for="bulk-assign-notes">Notes (optional):</label>
                <textarea id="bulk-assign-notes" rows="4"></textarea>
            </div>
            <div class="selected-po-list">
                <strong>Selected POs:</strong>
                ${selectedPOLines.map(po => `<div class="po-item">✓ ${escapeHtml(po.po_number)}-${escapeHtml(po.po_line)}</div>`).join('')}
            </div>
            <div class="modal-actions">
                <button type="submit" class="btn-primary">✓ Confirm Assignment</button>
                <button type="button" onclick="closeAssignmentModal()" class="btn-secondary">Cancel</button>
            </div>
        </form>
    `;
    
    modal.style.display = 'flex';
    
    loadAssignableUsers();
}

function closeAssignmentModal() {
    const modal = document.getElementById('assignment-modal');
    if (modal) {
        modal.style.display = 'none';
    }
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
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Assigning...';
    
    try {
        const payload = {
            po_ids: selectedPOLines.map(po => po.po_id),
            assigned_to_user_id: userId,
            assignment_notes: notes
        };
        
        const response = await apiCall(API_ENDPOINTS.CREATE_ASSIGNMENT, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        
        if (response) {
            alert(`✓ Successfully assigned ${selectedPOLines.length} PO line(s)!`);
            closeAssignmentModal();
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

// ============================================================================
// SECTION: MY ASSIGNMENTS
// ============================================================================

async function loadMyAssignments() {
    const tableDiv = document.getElementById('my-assignments-table');
    if (!tableDiv) {
        console.error('My assignments table div not found!');
        return;
    }
    
    tableDiv.innerHTML = '<div class="loading">🔄 Loading my assignments...</div>';
    
    try {
        const data = await apiCall(API_ENDPOINTS.MY_ASSIGNMENTS, {
            method: 'GET'
        });
        
        console.log('My assignments:', data);
        
        if (data && (data.pending.length > 0 || data.approved.length > 0 || data.rejected.length > 0)) {
            let html = '<h3>My Assignments</h3>';
            
            ['pending', 'approved', 'rejected'].forEach(status => {
                if (data[status].length > 0) {
                    html += `<h4>${status.charAt(0).toUpperCase() + status.slice(1)}</h4>`;
                    html += '<div class="assignments-grid">';
                    data[status].forEach(assignment => {
                        html += renderMyAssignmentCard(assignment, status === 'pending');
                    });
                    html += '</div>';
                }
            });
            
            tableDiv.innerHTML = html;
        } else {
            tableDiv.innerHTML = '<div class="empty-state"><p>No assignments found</p></div>';
        }
    } catch (error) {
        console.error('Failed to load my assignments:', error);
        tableDiv.innerHTML = `<div class="error">❌ Failed to load assignments: ${error.message}</div>`;
    }
}

// ============================================================================
// SECTION: CREATED ASSIGNMENTS
// ============================================================================

async function loadCreatedAssignments() {
    const tableDiv = document.getElementById('created-assignments-table');
    if (!tableDiv) {
        console.error('Created assignments table div not found!');
        return;
    }
    
    tableDiv.innerHTML = '<div class="loading">🔄 Loading created assignments...</div>';
    
    try {
        const data = await apiCall(API_ENDPOINTS.CREATED_ASSIGNMENTS, {
            method: 'GET'
        });
        
        console.log('Created assignments:', data);
        
        if (data && data.length > 0) {
            let html = '<h3>Created Assignments</h3>';
            html += '<div class="assignments-grid">';
            
            data.forEach(assignment => {
                html += renderCreatedAssignmentCard(assignment);
            });
            
            html += '</div>';
            tableDiv.innerHTML = html;
        } else {
            tableDiv.innerHTML = '<div class="empty-state"><p>No created assignments found</p></div>';
        }
    } catch (error) {
        console.error('Failed to load created assignments:', error);
        tableDiv.innerHTML = `<div class="error">❌ Failed to load assignments: ${error.message}</div>`;
    }
}

// ============================================================================
// RENDERING HELPERS
// ============================================================================

function renderMyAssignmentCard(assignment, showActions) {
    let html = '<div class="card">';
    html += `<h4>Assignment #${escapeHtml(assignment.id.substring(0, 8))}</h4>`;
    html += `<p><strong>PO Count:</strong> ${assignment.po_count}</p>`;
    html += `<p><strong>Assigned By:</strong> ${escapeHtml(assignment.assigned_by_name)}</p>`;
    html += `<p><strong>Status:</strong> <span class="badge badge-${assignment.status.toLowerCase()}">${escapeHtml(assignment.status)}</span></p>`;
    html += `<p><strong>Created:</strong> ${formatDate(assignment.created_at)}</p>`;
    
    if (assignment.assignment_notes) {
        html += `<p><strong>Notes:</strong> ${escapeHtml(assignment.assignment_notes)}</p>`;
    }
    
    if (showActions && assignment.status === 'PENDING') {
        html += '<div class="card-actions">';
        html += `<button onclick="respondToAssignment('${assignment.id}', 'APPROVE')" class="btn-primary">✓ Approve</button>`;
        html += `<button onclick="respondToAssignment('${assignment.id}', 'REJECT')" class="btn-danger">✗ Reject</button>`;
        html += '</div>';
    }
    
    html += '</div>';
    return html;
}

function renderCreatedAssignmentCard(assignment) {
    let html = '<div class="card">';
    html += `<h4>Assignment #${escapeHtml(assignment.id.substring(0, 8))}</h4>`;
    html += `<p><strong>PO Count:</strong> ${assignment.po_count}</p>`;
    html += `<p><strong>Assigned To:</strong> ${escapeHtml(assignment.assigned_to_name)}</p>`;
    html += `<p><strong>Status:</strong> <span class="badge badge-${assignment.status.toLowerCase()}">${escapeHtml(assignment.status)}</span></p>`;
    html += `<p><strong>Created:</strong> ${formatDate(assignment.created_at)}</p>`;
    html += '</div>';
    return html;
}

async function respondToAssignment(assignmentId, action) {
    let rejectionReason = '';
    
    if (action === 'REJECT') {
        rejectionReason = prompt('Please provide a rejection reason:');
        if (!rejectionReason) return;
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
            alert(`✅ Assignment ${action.toLowerCase()}ed successfully!`);
            loadMyAssignments();
        }
    } catch (error) {
        alert(`❌ Failed to respond: ${error.message}`);
    }
}

// ============================================================================
// PAGINATION
// ============================================================================

function renderAssignmentPagination(totalCount, currentPage) {
    const paginationDiv = document.getElementById('assignment-pagination');
    if (!paginationDiv) {
        console.error('Pagination div not found!');
        return;
    }
    
    const perPage = 100;
    const totalPages = Math.ceil(totalCount / perPage);
    
    let html = '<div class="pagination">';
    
    if (currentPage > 1) {
        html += `<button class="pagination-btn" data-page="${currentPage - 1}">« Previous</button>`;
    }
    
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
        const active = i === currentPage ? 'active' : '';
        html += `<button class="pagination-btn ${active}" data-page="${i}">${i}</button>`;
    }
    
    if (totalPages > 5) {
        html += '<span>...</span>';
        html += `<button class="pagination-btn" data-page="${totalPages}">${totalPages}</button>`;
    }
    
    if (currentPage < totalPages) {
        html += `<button class="pagination-btn" data-page="${currentPage + 1}">Next »</button>`;
    }
    
    html += `<span class="page-info">Page ${currentPage} of ${totalPages} (${totalCount} total)</span>`;
    html += '</div>';
    
    paginationDiv.innerHTML = html;

    // Attach event listeners to pagination buttons
    const paginationButtons = document.querySelectorAll('.pagination-btn');
    paginationButtons.forEach(button => {
        button.addEventListener('click', () => {
            const page = parseInt(button.getAttribute('data-page'));
            loadAvailablePOLinesForAssignment(page);
        });
    });
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function formatCurrency(amount) {
    if (!amount && amount !== 0) return 'N/A';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

function getStatusBadgeClass(status) {
    if (!status) return 'secondary';
    
    const statusLower = status.toLowerCase();
    if (statusLower.includes('closed') || statusLower.includes('completed')) return 'success';
    if (statusLower.includes('pending')) return 'warning';
    if (statusLower.includes('cancelled') || statusLower.includes('rejected')) return 'danger';
    return 'info';
}

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

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}