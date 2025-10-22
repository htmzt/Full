// Upload functions

async function uploadPOFile(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('po-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('po-upload-result', 'Please select a file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const resultDiv = document.getElementById('po-upload-result');
    resultDiv.innerHTML = '<div class="loading"></div> Uploading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.UPLOAD_PO, {
            method: 'POST',
            body: formData
        });
        
        if (data) {
            resultDiv.innerHTML = `
                <div class="success">
                    <h4>✅ Upload Successful!</h4>
                    <p><strong>Batch ID:</strong> ${data.batch_id}</p>
                    <p><strong>Total Rows:</strong> ${data.total_rows}</p>
                    <p><strong>Valid Rows:</strong> ${data.valid_rows}</p>
                    <p><strong>Invalid Rows:</strong> ${data.invalid_rows}</p>
                    <p><strong>Duration:</strong> ${data.processing_duration}s</p>
                </div>
            `;
            
            // Clear file input
            fileInput.value = '';
            
            // Reload upload history
            loadUploadHistory();
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Upload failed: ${error.message}</div>`;
    }
}

async function uploadAcceptanceFile(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('acceptance-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('acceptance-upload-result', 'Please select a file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const resultDiv = document.getElementById('acceptance-upload-result');
    resultDiv.innerHTML = '<div class="loading"></div> Uploading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.UPLOAD_ACCEPTANCE, {
            method: 'POST',
            body: formData
        });
        
        if (data) {
            resultDiv.innerHTML = `
                <div class="success">
                    <h4>✅ Upload Successful!</h4>
                    <p><strong>Batch ID:</strong> ${data.batch_id}</p>
                    <p><strong>Total Rows:</strong> ${data.total_rows}</p>
                    <p><strong>Valid Rows:</strong> ${data.valid_rows}</p>
                    <p><strong>Invalid Rows:</strong> ${data.invalid_rows}</p>
                    <p><strong>Duration:</strong> ${data.processing_duration}s</p>
                </div>
            `;
            
            // Clear file input
            fileInput.value = '';
            
            // Reload upload history
            loadUploadHistory();
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Upload failed: ${error.message}</div>`;
    }
}

async function loadUploadHistory() {
    const historyDiv = document.getElementById('upload-history');
    historyDiv.innerHTML = '<div class="loading"></div> Loading...';
    
    try {
        const data = await apiCall(API_ENDPOINTS.UPLOAD_HISTORY, {
            method: 'GET'
        });
        
        if (data && data.results && data.results.length > 0) {
            let html = '<table><thead><tr>';
            html += '<th>File Type</th>';
            html += '<th>Filename</th>';
            html += '<th>Status</th>';
            html += '<th>Total Rows</th>';
            html += '<th>Valid/Invalid</th>';
            html += '<th>Uploaded At</th>';
            html += '</tr></thead><tbody>';
            
            data.results.forEach(upload => {
                html += '<tr>';
                html += `<td>${upload.file_type}</td>`;
                html += `<td>${upload.original_filename}</td>`;
                html += `<td><span class="badge badge-${upload.status.toLowerCase()}">${upload.status}</span></td>`;
                html += `<td>${upload.total_rows}</td>`;
                html += `<td>${upload.valid_rows} / ${upload.invalid_rows}</td>`;
                html += `<td>${formatDate(upload.uploaded_at)}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            historyDiv.innerHTML = html;
        } else {
            historyDiv.innerHTML = '<div class="empty-state"><p>No upload history found</p></div>';
        }
    } catch (error) {
        historyDiv.innerHTML = `<div class="error">Failed to load upload history: ${error.message}</div>`;
    }
}