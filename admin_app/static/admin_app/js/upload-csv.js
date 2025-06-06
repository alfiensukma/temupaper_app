Dropzone.autoDiscover = false;

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
const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {
    const importBtn = document.getElementById('importBtn');
    const csvInput = document.getElementById('csvInput');
    const refInput = document.getElementById('referensiCsvInput');

    const csvDropzone = new Dropzone("#csvDropzone", {
        url: "#",
        maxFiles: 1,
        acceptedFiles: ".csv",
        autoProcessQueue: false,
        clickable: true,
        addRemoveLinks: true,
        dictRemoveFile: "Hapus file",
        dictInvalidFileType: "Hanya file CSV yang diperbolehkan",
        init: function() {
            this.on("addedfile", function(file) {
                if (!file.name.toLowerCase().endsWith('.csv')) {
                    this.removeFile(file);
                    Swal.fire({ icon: 'error', title: 'Error', text: 'Hanya file CSV' });
                    return;
                }
                try {
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    csvInput.files = dataTransfer.files;
                } catch (e) {
                    console.error('Error setting csvInput.files:', e);
                }
                document.querySelector("#csvDropzone .dz-message").innerHTML = `<p>${file.name}</p>`;
                updateButtonState();
            });
            this.on("removedfile", function() {
                csvInput.value = '';
                document.querySelector("#csvDropzone .dz-message").innerHTML = `
                    <i class="fas fa-file-csv fa-5x mb-3" style="color: #3b82f6;"></i>
                    <p style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0;">Seret file CSV di sini atau klik untuk memilih</p>
                    <p style="font-size: 0.9rem; color: #60a5fa;">(Hanya file CSV yang diperbolehkan)</p>`;
                updateButtonState();
            });
        }
    });

    const refDropzone = new Dropzone("#referensiCsvDropzone", {
        url: "#",
        maxFiles: 1,
        acceptedFiles: ".csv",
        autoProcessQueue: false,
        clickable: true,
        addRemoveLinks: true,
        dictRemoveFile: "Hapus file",
        dictInvalidFileType: "Hanya file CSV yang diperbolehkan",
        init: function() {
            this.on("addedfile", function(file) {
                if (!file.name.toLowerCase().endsWith('.csv')) {
                    this.removeFile(file);
                    Swal.fire({ icon: 'error', title: 'Error', text: 'Hanya file CSV' });
                    return;
                }
                try {
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    refInput.files = dataTransfer.files;
                } catch (e) {
                    console.error('Error setting refInput.files:', e);
                }
                document.querySelector("#referensiCsvDropzone .dz-message").innerHTML = `<p>${file.name}</p>`;
                updateButtonState();
            });
            this.on("removedfile", function() {
                refInput.value = '';
                document.querySelector("#referensiCsvDropzone .dz-message").innerHTML = `
                    <i class="fas fa-file-csv fa-5x mb-3" style="color: #3b82f6;"></i>
                    <p style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0;">Seret file CSV di sini atau klik untuk memilih</p>
                    <p style="font-size: 0.9rem; color: #60a5fa;">(Hanya file CSV yang diperbolehkan)</p>`;
                updateButtonState();
            });
        }
    });

    function updateButtonState() {
        const hasCsv = csvInput.files.length > 0;
        const hasRef = refInput.files.length > 0;
        importBtn.disabled = !(hasCsv && hasRef);
    }

    importBtn.addEventListener('click', function() {
        Swal.fire({
            title: 'Mulai Import?',
            text: 'Pastikan file sudah benar. Data sebelumnya akan ditimpa.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Ya, mulai!',
            cancelButtonText: 'Batal'
        }).then((result) => {
            if (result.isConfirmed) {
                document.getElementById('uploadSection').classList.add('d-none');
                document.getElementById('progressSection').classList.remove('d-none');
                document.getElementById('importLog').innerHTML = ''; // Reset log

                const formData = new FormData();
                formData.append('csv_file', csvInput.files[0]);
                formData.append('referensi_csv_file', refInput.files[0]);
                formData.append('csrfmiddlewaretoken', csrftoken);

                fetch('/admin-app/upload-temp-files/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrftoken
                    }
                })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (data.error) {
                            throw new Error(data.error);
                        }

                        // Mulai proses impor
                        const importData = new FormData();
                        importData.append('csv_path', data.csv_path);
                        importData.append('ref_path', data.ref_path);
                        importData.append('csrfmiddlewaretoken', csrftoken);

                        fetch('/admin-app/start-import/', {
                            method: 'POST',
                            body: importData,
                            headers: {
                                'X-CSRFToken': csrftoken
                            }
                        })
                            .then(response => {
                                if (!response.ok) {
                                    throw new Error(`Start import failed: ${response.status} ${response.statusText}`);
                                }
                                return response.json();
                            })
                            .then(data => {
                                if (data.error) {
                                    throw new Error(data.error);
                                }
                                pollProgress();
                            })
                            .catch(error => {
                                Swal.fire({
                                    icon: 'error',
                                    title: 'Error',
                                    text: 'Gagal memulai impor: ' + error.message
                                });
                                resetUI();
                            });
                    })
                    .catch(error => {
                        Swal.fire({
                            icon: 'error',
                            title: 'Error',
                            text: 'Gagal mengunggah file: ' + error.message
                        });
                        resetUI();
                    });
            }
        });
    });

    function pollProgress() {
        const progressBar = document.getElementById('importProgress');
        const stepDetail = document.getElementById('stepDetail');
        const importLog = document.getElementById('importLog');
        let lastLogIndex = 0; // Track log yang sudah ditampilkan
        const pollInterval = setInterval(() => {
            fetch('/admin-app/get-progress/', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Get progress failed: ${response.status} ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (!progressBar || !stepDetail || !importLog) {
                        console.error('UI elements missing:', { progressBar, stepDetail, importLog });
                        clearInterval(pollInterval);
                        return;
                    }
                    progressBar.style.width = `${data.progress_percent}%`;
                    progressBar.textContent = `Step ${data.step}/${data.total_steps}`;
                    stepDetail.textContent = data.progress_message || 'No message';

                    // Tambah log baru ke importLog
                    if (data.log && data.log.length > lastLogIndex) {
                        for (let i = lastLogIndex; i < data.log.length; i++) {
                            const logMessage = data.log[i];
                            const isError = logMessage.toLowerCase().includes('error');
                            importLog.innerHTML += `
                                <li class="list-group-item ${isError ? 'text-danger' : 'text-success'}">
                                    ${logMessage}
                                </li>`;
                        }
                        lastLogIndex = data.log.length;
                        importLog.scrollTop = importLog.scrollHeight; // Auto-scroll ke bawah
                    }

                    if (data.message) {
                        if (data.message.toLowerCase().includes('error')) {
                            Swal.fire({
                                icon: 'error',
                                title: 'Error',
                                text: data.message
                            });
                            resetUI();
                            clearInterval(pollInterval);
                        } else if (data.message.includes('selesai')) {
                            Swal.fire({
                                icon: 'success',
                                title: 'Selesai',
                                text: data.message
                            });
                            resetUI();
                            clearInterval(pollInterval);
                        }
                    }
                    if (!data.is_processing) {
                        clearInterval(pollInterval);
                    }
                })
                .catch(error => {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: 'Gagal memperbarui progres: ' + error.message
                    });
                    resetUI();
                    clearInterval(pollInterval);
                });
        }, 500); // Poll setiap 500ms
        // Berhenti setelah 5 menit
        setTimeout(() => {
            clearInterval(pollInterval);
        }, 300000);
    }

    function resetUI() {
        document.getElementById('uploadSection').classList.remove('d-none');
        document.getElementById('progressSection').classList.add('d-none');
        csvDropzone.removeAllFiles();
        refDropzone.removeAllFiles();
        importBtn.disabled = true;
        document.getElementById('importLog').innerHTML = ''; // Reset log
    }

    document.addEventListener('click', function(event) {
        if (event.target.id === 'backToUpload') {
            resetUI();
        }
    });
});