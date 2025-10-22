// Merged Data functions

let currentPage = 1;
let currentFilters = {};

async function loadMergedData(page = 1) {
    const tableDiv = document.getElementById('merged-data-table');
    tableDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    currentPage = page;
    
    // Get filter values
    const search = document.getElementById('search-merged').value;
    const status = document.getElementById('filter-status').value;
    const category = document.getElementById('filter-category').value;
    
    // Build query params
    let url = `${API_ENDPOINTS.MERGED_DATA}?page=${page}&per_page=50`;
    
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    
    try {
        const data = await apiCall(url, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '<div style="overflow-x: auto;"><table><thead><tr>';
            html += '<th>PO Number</th>';
            html += '<th>Line No</th>';
            html += '<th>Project</th>';
            html += '<th>Item Description</th>';
            html += '<th>Category</th>';
            html += '<th>Amount</th>';
            html += '<th>Status</th>';
            html += '<th>Assigned</th>';
            html += '<th>External PO</th>';
            html += '</tr></thead><tbody>';
            
            data.results.forEach(po => {
                html += '<tr>';
                html += `<td>${po.po_number}</td>`;
                html += `<td>${po.po_line_no}</td>`;
                html += `<td>${po.project_name || 'N/A'}</td>`;
                html += `<td>${po.item_description ? po.item_description.substring(0, 50) + '...' : 'N/A'}</td>`;
                html += `<td>${po.category || 'N/A'}</td>`;
                html += `<td>${formatCurrency(po.line_amount)}</td>`;
                html += `<td><span class="badge badge-${getStatusBadgeClass(po.status)}">${po.status || 'N/A'}</span></td>`;
                html += `<td>${po.is_assigned ? '✅' : '❌'}</td>`;
                html += `<td>${po.has_external_po ? '✅' : '❌'}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table></div>';
            tableDiv.innerHTML = html;
            
            // Show pagination
            renderPagination(data.count, page);
        } else {
            tableDiv.innerHTML = '<div class="empty-state"><p>No merged data found</p></div>';
        }
    } catch (error) {
        tableDiv.innerHTML = `<div class="error">Failed to load merged data: ${error.message}</div>`;
    }
}

function renderPagination(totalCount, currentPage) {
    const paginationDiv = document.getElementById('merged-data-pagination');
    const perPage = 50;
    const totalPages = Math.ceil(totalCount / perPage);
    
    if (totalPages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }
    
    let html = '<div class="pagination">';
    
    // Previous button
    if (currentPage > 1) {
        html += `<button onclick="loadMergedData(${currentPage - 1})">Previous</button>`;
    }
    
    // Page numbers (show max 5 pages)
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        html += `<button class="${activeClass}" onclick="loadMergedData(${i})">${i}</button>`;
    }
    
    // Next button
    if (currentPage < totalPages) {
        html += `<button onclick="loadMergedData(${currentPage + 1})">Next</button>`;
    }
    
    html += `</div><p style="text-align: center; margin-top: 10px;">Page ${currentPage} of ${totalPages} (${totalCount} total records)</p>`;
    paginationDiv.innerHTML = html;
}

async function exportMergedData() {
    try {
        // Get filter values
        const search = document.getElementById('search-merged').value;
        const status = document.getElementById('filter-status').value;
        const category = document.getElementById('filter-category').value;
        
        // Build query params
        let url = API_ENDPOINTS.EXPORT_MERGED_DATA;
        const params = [];
        
        if (search) params.push(`search=${encodeURIComponent(search)}`);
        if (status) params.push(`status=${encodeURIComponent(status)}`);
        if (category) params.push(`category=${encodeURIComponent(category)}`);
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        const blob = await apiCall(url, {
            method: 'GET'
        });
        
        if (blob) {
            downloadFile(blob, `merged_data_${new Date().toISOString().split('T')[0]}.xlsx`);
            alert('Export successful!');
        }
    } catch (error) {
        alert(`Export failed: ${error.message}`);
    }
}