// Merge functions

async function checkMergeStatus() {
    const resultDiv = document.getElementById('merge-status-result');
    resultDiv.innerHTML = '<div class="loading"></div> Checking...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.MERGE_STATUS, {
            method: 'GET'
        });
        
        if (data) {
            let html = '<div class="info-box">';
            html += `<p><strong>PO Data:</strong> ${data.has_po_data ? '✅ Available' : '❌ Not uploaded'} (${data.po_count} records)</p>`;
            html += `<p><strong>Acceptance Data:</strong> ${data.has_acceptance_data ? '✅ Available' : '❌ Not uploaded'} (${data.acceptance_count} records)</p>`;
            html += `<p><strong>Ready to Merge:</strong> ${data.ready_to_merge ? '✅ Yes' : '❌ No'}</p>`;
            html += '</div>';
            
            resultDiv.innerHTML = html;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Failed to check status: ${error.message}</div>`;
    }
}

async function triggerMerge() {
    if (!confirm('Are you sure you want to trigger the merge? This will replace existing merged data.')) {
        return;
    }
    
    const resultDiv = document.getElementById('merge-result');
    resultDiv.innerHTML = '<div class="loading"></div> Merging data...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.TRIGGER_MERGE, {
            method: 'POST'
        });
        
        if (data) {
            resultDiv.innerHTML = `
                <div class="success">
                    <h4>✅ Merge Successful!</h4>
                    <p><strong>Batch ID:</strong> ${data.batch_id}</p>
                    <p><strong>Merged Records:</strong> ${data.merged_records}</p>
                    <p><strong>PO Records:</strong> ${data.po_records}</p>
                    <p><strong>Acceptance Records:</strong> ${data.acceptance_records}</p>
                    <p><strong>Merged At:</strong> ${formatDate(data.merged_at)}</p>
                </div>
            `;
            
            // Refresh merge status
            checkMergeStatus();
            loadMergeHistory();
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Merge failed: ${error.message}</div>`;
    }
}

async function loadMergeHistory() {
    const historyDiv = document.getElementById('merge-history');
    historyDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.MERGE_HISTORY, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '<table><thead><tr>';
            html += '<th>Batch ID</th>';
            html += '<th>Total Records</th>';
            html += '<th>PO Records</th>';
            html += '<th>Acceptance Records</th>';
            html += '<th>Status</th>';
            html += '<th>Merged At</th>';
            html += '</tr></thead><tbody>';
            
            data.results.forEach(merge => {
                html += '<tr>';
                html += `<td>${merge.batch_id}</td>`;
                html += `<td>${merge.total_records}</td>`;
                html += `<td>${merge.po_records_count || 0}</td>`;
                html += `<td>${merge.acceptance_records_count || 0}</td>`;
                html += `<td><span class="badge badge-${merge.status.toLowerCase()}">${merge.status}</span></td>`;
                html += `<td>${formatDate(merge.merged_at)}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            historyDiv.innerHTML = html;
        } else {
            historyDiv.innerHTML = '<div class="empty-state"><p>No merge history found</p></div>';
        }
    } catch (error) {
        historyDiv.innerHTML = `<div class="error">Failed to load merge history: ${error.message}</div>`;
    }
}