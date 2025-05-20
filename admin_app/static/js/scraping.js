function initSelect2Topics() {
    // Destroy jika sudah pernah diinisialisasi
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

    // Inisialisasi ulang setiap Unicorn selesai render komponen
    document.addEventListener("unicorn:after", function() {
        initSelect2Topics();
    });

    const startBtn = document.getElementById('startScrapingBtn');
    const scrapingInfo = document.getElementById('scrapingInfo');
    const scrapingStepInfo = document.getElementById('scrapingStepInfo');
    const scrapingProgressBar = document.getElementById('scrapingProgressBar');
    const scrapingLog = document.getElementById('scrapingLog');

    startBtn.addEventListener('click', async function() {
        const selectedTopics = $('#topics').val();
        if (!selectedTopics || selectedTopics.length === 0) {
            alert('Pilih minimal satu topik!');
            return;
        }

        scrapingInfo.style.display = '';
        scrapingStepInfo.textContent = 'Memulai proses scraping...';
        scrapingProgressBar.style.width = '0%';
        scrapingProgressBar.textContent = '0%';
        scrapingLog.innerHTML = '';

        for (let i = 0; i < selectedTopics.length; i++) {
            const topic = selectedTopics[i];
            scrapingStepInfo.textContent = `Scraping topik: "${topic}" (${i+1} dari ${selectedTopics.length})...`;
            // Ubah format jam ke 24 jam
            scrapingLog.innerHTML += `<li class="list-group-item">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Mulai scraping topik: <b>${topic}</b></li>`;

            try {
                const response = await fetch(`/fetch-papers/?query=${encodeURIComponent(topic)}`);
                if (response.ok) {
                    const blob = await response.blob();
                    const filename = `scraping_${new Date().toISOString().replace(/[-:T]/g,'').slice(0,15)}.zip`;
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);

                    // Ubah format jam ke 24 jam
                    scrapingLog.innerHTML += `<li class="list-group-item text-success">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Selesai scraping topik: <b>${topic}</b> (file terunduh)</li>`;
                } else {
                    let errMsg = "Gagal download file";
                    try {
                        const err = await response.json();
                        errMsg = err.error || errMsg;
                    } catch {}
                    // Ubah format jam ke 24 jam
                    scrapingLog.innerHTML += `<li class="list-group-item text-danger">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Gagal scraping topik: <b>${topic}</b> (${errMsg})</li>`;
                }
            } catch (err) {
                // Ubah format jam ke 24 jam
                scrapingLog.innerHTML += `<li class="list-group-item text-danger">[${new Date().toLocaleTimeString('en-GB', { hour12: false })}] Error scraping topik: <b>${topic}</b> (${err})</li>`;
            }

            let progress = Math.round(((i+1)/selectedTopics.length)*100);
            scrapingProgressBar.style.width = progress + '%';
            scrapingProgressBar.textContent = progress + '%';
        }

        scrapingStepInfo.textContent = 'Proses scraping selesai!';
    });
});