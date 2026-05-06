document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('cv-file');
    const fileMsg = document.querySelector('.file-msg');
    const form = document.getElementById('evaluation-form');
    const submitBtn = document.getElementById('submit-btn');
    const spinner = document.getElementById('submit-spinner');
    const errorMsg = document.getElementById('error-message');
    
    const uploadPanel = document.getElementById('upload-panel');
    const statusPanel = document.getElementById('status-panel');
    const resultPanel = document.getElementById('result-panel');
    
    const logList = document.getElementById('log-list');
    const progressBar = document.getElementById('progress-bar');
    const reportContent = document.getElementById('report-content');
    
    const restartBtn = document.getElementById('restart-btn');
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileMsg.textContent = e.target.files[0].name;
            fileMsg.style.color = '#f8fafc';
        } else {
            fileMsg.textContent = 'Chọn một file PDF hoặc kéo thả vào đây';
            fileMsg.style.color = 'var(--text-muted)';
        }
    });
    
    function addLog(message) {
        const li = document.createElement('li');
        const time = new Date().toLocaleTimeString();
        li.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
        logList.appendChild(li);
        
        // Auto scroll
        const terminal = document.querySelector('.terminal');
        terminal.scrollTop = terminal.scrollHeight;
    }
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showError("Vui lòng chọn một file CV.");
            return;
        }
        
        // Reset state
        errorMsg.classList.add('hidden');
        submitBtn.disabled = true;
        spinner.classList.remove('hidden');
        submitBtn.querySelector('span').textContent = 'Đang tải lên & Kiểm tra...';
        
        const formData = new FormData();
        formData.append('cv_file', file);
        formData.append('jd_text', document.getElementById('jd-text').value);
        
        try {
            // Step 1: Submit Job
            const res = await fetch('/api/v1/jobs/submit', {
                method: 'POST',
                body: formData
            });
            
            const data = await res.json();
            
            if (!res.ok) {
                throw new Error(data.detail || "Upload failed");
            }
            
            // Success upload, switch panels
            uploadPanel.classList.add('hidden');
            statusPanel.classList.remove('hidden');
            
            // Step 2: Start SSE Stream
            startStream(data.job_id);
            
        } catch (err) {
            showError(err.message);
            submitBtn.disabled = false;
            spinner.classList.add('hidden');
            submitBtn.querySelector('span').textContent = 'Bắt đầu Phân tích AI';
        }
    });
    
    let currentJobId = null;

    function startStream(jobId) {
        currentJobId = jobId;
        const eventSource = new EventSource(`/api/v1/jobs/stream/${jobId}`);
        let progress = 10;
        progressBar.style.width = `${progress}%`;
        
        eventSource.addEventListener('status', (e) => {
            addLog(e.data);
            progress += 10;
            if (progress > 95) progress = 95;
            progressBar.style.width = `${progress}%`;
        });
        
        eventSource.addEventListener('complete', (e) => {
            addLog("Phân tích hoàn tất! Đang chuẩn bị báo cáo...");
            progressBar.style.width = '100%';
            
            const data = JSON.parse(e.data);
            reportContent.innerHTML = data.report_html;
            
            setTimeout(() => {
                statusPanel.classList.add('hidden');
                resultPanel.classList.remove('hidden');
                eventSource.close();
            }, 1000);
        });
        
        eventSource.addEventListener('error', (e) => {
            console.error("SSE Error:", e);
            addLog(`Lỗi: Mất kết nối hoặc quá trình xử lý thất bại.`);
            eventSource.close();
            
            // Offer to go back
            setTimeout(() => {
                uploadPanel.classList.remove('hidden');
                statusPanel.classList.add('hidden');
                submitBtn.disabled = false;
                spinner.classList.add('hidden');
                submitBtn.querySelector('span').textContent = 'Bắt đầu Phân tích AI';
            }, 3000);
        });
    }
    
    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.classList.remove('hidden');
    }
    
    restartBtn.addEventListener('click', () => {
        resultPanel.classList.add('hidden');
        uploadPanel.classList.remove('hidden');
        form.reset();
        fileMsg.textContent = 'Chọn một file PDF hoặc kéo thả vào đây';
        fileMsg.style.color = 'var(--text-muted)';
        submitBtn.disabled = false;
        spinner.classList.add('hidden');
        submitBtn.querySelector('span').textContent = 'Bắt đầu Phân tích AI';
        logList.innerHTML = '<li><span class="log-time">[Hệ thống]</span> Đang khởi tạo hệ thống phân tích LangGraph...</li>';
        progressBar.style.width = '0%';
    });
    
    downloadPdfBtn.addEventListener('click', () => {
        if (!currentJobId) {
            showError("Không có báo cáo nào để tải xuống.");
            return;
        }
        
        // Trigger download from backend API using WeasyPrint
        window.open(`/api/v1/jobs/download/${currentJobId}`, '_blank');
    });
});
