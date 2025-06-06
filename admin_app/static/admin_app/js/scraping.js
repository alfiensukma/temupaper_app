function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function initSelect2Topics() {
    if ($('#topics').hasClass("select2-hidden-accessible")) {
        $('#topics').select2('destroy');
    }
    $('#topics').select2({
        width: '100%',
        placeholder: "Pilih topik scraping",
        allowClear: true
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initSelect2Topics();
    document.addEventListener("unicorn:after", function() {
        initSelect2Topics();
    });

    const startBtn = document.getElementById('startScrapingBtn');
    const downloadBtn = document.getElementById('downloadResultBtn');
    const scrapingInfo = document.getElementById('scrapingInfo');
    const scrapingStepInfo = document.getElementById('scrapingStepInfo');
    const scrapingProgressBar = document.getElementById('scrapingProgressBar');
    const scrapingLog = document.getElementById('scrapingLog');
    
    let currentTimestamp = null;

    downloadBtn.classList.add('d-none');

    startBtn.addEventListener('click', async function() {
        const selectedValues = $('#topics').val();
        if (!selectedValues || selectedValues.length === 0) {
            alert('Pilih minimal satu topik!');
            return;
        }
        
        // Parse nilai dari format "id|name" menjadi array objek
        const selectedTopics = selectedValues.map(value => {
            const [id, name] = value.split('|');
            return { id, name };
        });

        scrapingInfo.style.display = '';
        scrapingStepInfo.textContent = 'Memulai proses scraping...';
        scrapingProgressBar.style.width = '0%';
        scrapingProgressBar.textContent = '0%';
        scrapingLog.innerHTML = '';
        
        downloadBtn.classList.add('d-none');
        
        currentTimestamp = new Date().toISOString().replace(/[-:.TZ]/g,'').slice(0,15);
        
        const topicResults = [];
        let allSuccess = true;
        
        for (let i = 0; i < selectedTopics.length; i++) {
            const topic = selectedTopics[i];
            scrapingStepInfo.textContent = `Scraping topik: "${topic.name}" (${i+1} dari ${selectedTopics.length})...`;
            
            scrapingLog.innerHTML += `<li class="list-group-item">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Mulai scraping topik: <b>${topic.name}</b></li>`;

            try {
                const url = new URL('/scrape-topic/', window.location.origin);
                url.searchParams.append('topic_id', topic.id);
                url.searchParams.append('topic_name', topic.name);
                url.searchParams.append('csv_timestamp', currentTimestamp);
                
                const response = await fetch(url);
                const data = await response.json();
                
                if (response.ok) {
                    scrapingLog.innerHTML += `<li class="list-group-item text-success">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Selesai scraping topik: <b>${topic.name}</b> (${data.count} paper)</li>`;
                    
                    topicResults.push({
                        topic: topic.name,
                        status: "success",
                        count: data.count,
                        timestamp: new Date().toISOString()
                    });
                } else {
                    allSuccess = false;
                    let errMsg = data.error || "Gagal scraping";
                    
                    scrapingLog.innerHTML += `<li class="list-group-item text-danger">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Gagal scraping topik: <b>${topic.name}</b> (${errMsg})</li>`;
                    
                    topicResults.push({
                        topic: topic.name,
                        status: "error",
                        message: errMsg,
                        timestamp: new Date().toISOString()
                    });
                }
            } catch (err) {
                allSuccess = false;
                scrapingLog.innerHTML += `<li class="list-group-item text-danger">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Error scraping topik: <b>${topic.name}</b> (${err.message})</li>`;
                
                topicResults.push({
                    topic: topic.name,
                    status: "error",
                    message: err.toString(),
                    timestamp: new Date().toISOString()
                });
            }

            let progress = Math.round(((i+1)/selectedTopics.length)*100);
            scrapingProgressBar.style.width = progress + '%';
            scrapingProgressBar.textContent = progress + '%';
        }

        scrapingStepInfo.textContent = 'Proses scraping selesai!';

        try {
            const successResults = topicResults.filter(result => result.status === "success");
            
            if (successResults.length > 0) {
                const response = await fetch('/admin-app/log-scraping-history/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        topics: selectedTopics.map(t => t.name),
                        results: topicResults,
                        timestamp: new Date().toISOString(),
                        success: true
                    })
                });
                
                if (response.ok) {
                    console.log('History scraping berhasil disimpan');
                } else {
                    console.error('Gagal menyimpan history scraping');
                }
            } else {
                console.log('Tidak ada scraping yang berhasil, history tidak disimpan');
            }
        } catch (err) {
            console.error('Error saat menyimpan history:', err);
        }
        
        if (allSuccess && topicResults.length > 0) {
            downloadBtn.classList.remove('d-none');
            scrapingLog.innerHTML += `<li class="list-group-item text-info">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Scraping selesai! Klik tombol Download Hasil untuk mengunduh file.</li>`;
        }
    });

    downloadBtn.addEventListener('click', async function() {
        if (!currentTimestamp) {
            alert('Tidak ada data untuk diunduh.');
            return;
        }
        
        try {
            scrapingLog.innerHTML += `<li class="list-group-item">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Mengunduh hasil scraping...</li>`;
            
            const downloadUrl = new URL('/download-results/', window.location.origin);
            downloadUrl.searchParams.append('timestamp', currentTimestamp);
            
            const response = await fetch(downloadUrl);
            
            if (response.ok) {
                const blob = await response.blob();
                const filename = `scraping_${currentTimestamp}.zip`;
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);

                scrapingLog.innerHTML += `<li class="list-group-item text-success">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] File hasil scraping berhasil diunduh</li>`;
            } else {
                const errorData = await response.json();
                scrapingLog.innerHTML += `<li class="list-group-item text-danger">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Gagal mengunduh hasil: ${errorData.error || 'Unknown error'}</li>`;
            }
        } catch (err) {
            scrapingLog.innerHTML += `<li class="list-group-item text-danger">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Error saat mengunduh hasil: ${err.message}</li>`;
        }
    });
});