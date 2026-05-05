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
            fileMsg.textContent = 'Choose a PDF file or drag it here';
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
            showError("Please select a CV file.");
            return;
        }
        
        // Reset state
        errorMsg.classList.add('hidden');
        submitBtn.disabled = true;
        spinner.classList.remove('hidden');
        submitBtn.querySelector('span').textContent = 'Uploading & Validating...';
        
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
            submitBtn.querySelector('span').textContent = 'Start AI Analysis';
        }
    });
    
    function startStream(jobId) {
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
            addLog("Analysis complete! Preparing report...");
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
            addLog(`Error: Connection lost or pipeline failed.`);
            eventSource.close();
            
            // Offer to go back
            setTimeout(() => {
                uploadPanel.classList.remove('hidden');
                statusPanel.classList.add('hidden');
                submitBtn.disabled = false;
                spinner.classList.add('hidden');
                submitBtn.querySelector('span').textContent = 'Start AI Analysis';
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
        fileMsg.textContent = 'Choose a PDF file or drag it here';
        fileMsg.style.color = 'var(--text-muted)';
        submitBtn.disabled = false;
        spinner.classList.add('hidden');
        submitBtn.querySelector('span').textContent = 'Start AI Analysis';
        logList.innerHTML = '<li><span class="log-time">[System]</span> Initializing LangGraph multi-agent pipeline...</li>';
        progressBar.style.width = '0%';
    });
    
    downloadPdfBtn.addEventListener('click', () => {
        const element = document.getElementById('report-content');
        const opt = {
            margin:       1,
            filename:     'AI_CV_Evaluation_Report.pdf',
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };
        
        // New Promise-based usage:
        html2pdf().set(opt).from(element).save();
    });
});
