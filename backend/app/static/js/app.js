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
    
    // Language toggle elements
    const langToggle = document.getElementById('lang-toggle');
    const langLabel = document.getElementById('lang-label');
    const reportLangToggle = document.getElementById('report-lang-toggle');
    const reportLangLabel = document.getElementById('report-lang-label');
    
    // Language dictionary
    const i18n = {
        vi: {
            title: 'Hệ thống Phân tích CV AI ',
            subtitle: 'Tải CV của bạn lên để nhận phân tích chuyên sâu từ AI đa luồng.',
            upload_label: 'Tải lên CV (PDF)',
            drag_drop: 'Chọn một file PDF hoặc kéo thả vào đây',
            jd_label: 'Mô tả công việc - JD (Tùy chọn)',
            jd_placeholder: 'Dán mô tả công việc vào đây để xem CV của bạn phù hợp với vị trí này như thế nào...',
            start_btn: 'Bắt đầu Phân tích AI',
            processing: 'AI Đang Xử Lý',
            init_log: 'Đang khởi tạo hệ thống phân tích LangGraph...',
            complete: 'Phân tích Hoàn tất',
            download_btn: 'Tải Báo Cáo PDF',
            restart_btn: 'Đánh giá CV Khác'
        },
        en: {
            title: 'AI CV Evaluation System ',
            subtitle: 'Upload your CV for deep analysis from our multi-agent AI.',
            upload_label: 'Upload CV (PDF)',
            drag_drop: 'Choose a PDF file or drag & drop here',
            jd_label: 'Job Description - JD (Optional)',
            jd_placeholder: 'Paste job description here to see how your CV fits this role...',
            start_btn: 'Start AI Analysis',
            processing: 'AI is Processing',
            init_log: 'Initializing LangGraph analysis system...',
            complete: 'Analysis Complete',
            download_btn: 'Download PDF Report',
            restart_btn: 'Evaluate Another CV'
        }
    };
    
    // Language state
    let currentLang = 'vi';
    
    function updateLangButtons() {
        const nextLang = currentLang === 'vi' ? 'EN' : 'VI';
        if (langLabel) langLabel.textContent = `🌐 ${nextLang}`;
        if (reportLangLabel) reportLangLabel.textContent = `🌐 ${nextLang}`;
    }
    
    function applyTranslations() {
        const dict = i18n[currentLang];
        
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (dict[key]) {
                if (key === 'title') {
                    el.innerHTML = dict[key] + '<span class="badge">Pro</span>';
                } else {
                    el.textContent = dict[key];
                }
            }
        });
        
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (dict[key]) {
                el.placeholder = dict[key];
            }
        });
    }

    function toggleLang() {
        currentLang = currentLang === 'vi' ? 'en' : 'vi';
        updateLangButtons();
        applyTranslations();
    }
    
    if (langToggle) {
        langToggle.addEventListener('click', toggleLang);
    }
    
    if (reportLangToggle) {
        reportLangToggle.addEventListener('click', async () => {
            toggleLang();
            // Re-render report in new language
            if (currentJobId) {
                try {
                    const res = await fetch(`/api/v1/jobs/report/${currentJobId}?lang=${currentLang}`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.report_html) {
                            reportContent.innerHTML = data.report_html;
                        }
                    }
                } catch (err) {
                    console.error('Failed to switch report language:', err);
                }
            }
        });
    }
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileMsg.textContent = e.target.files[0].name;
            fileMsg.style.color = '#f8fafc';
        } else {
            fileMsg.textContent = i18n[currentLang].drag_drop;
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
        formData.append('lang', currentLang);
        
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
            submitBtn.querySelector('span').textContent = i18n[currentLang].start_btn;
        }
    });
    
    let currentJobId = null;

    function startStream(jobId) {
        currentJobId = jobId;
        const eventSource = new EventSource(`/api/v1/jobs/stream/${jobId}?lang=${currentLang}`);
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
                submitBtn.querySelector('span').textContent = i18n[currentLang].start_btn;
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
        fileMsg.textContent = i18n[currentLang].drag_drop;
        fileMsg.style.color = 'var(--text-muted)';
        submitBtn.disabled = false;
        spinner.classList.add('hidden');
        submitBtn.querySelector('span').textContent = i18n[currentLang].start_btn;
        const initText = i18n[currentLang].init_log;
        logList.innerHTML = `<li><span class="log-time">[Hệ thống]</span> <span data-i18n="init_log">${initText}</span></li>`;
        progressBar.style.width = '0%';
    });
    
    downloadPdfBtn.addEventListener('click', () => {
        if (!currentJobId) {
            showError("Không có báo cáo nào để tải xuống.");
            return;
        }
        
        // Trigger download from backend API, pass current language
        window.open(`/api/v1/jobs/download/${currentJobId}?lang=${currentLang}`, '_blank');
    });
});
