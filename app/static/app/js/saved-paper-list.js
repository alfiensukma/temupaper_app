const INDONESIAN_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
};

let allPapers = window.allPapers || [];
let currentPage = 1;
const papersPerPage = 5;
let startPickerInstance = null;
let endPickerInstance = null;

function showNotification(message, type = 'success') {
    const existingNotification = document.getElementById('notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    const bgColor = type === 'success' ? 'bg-green-500' : 'bg-red-500';
    const icon = type === 'success' 
        ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>'
        : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>';

    const notification = document.createElement('div');
    notification.id = 'notification';
    notification.className = `fixed bottom-5 right-5 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 transform translate-x-full transition-transform duration-300`;
    notification.innerHTML = `
        <div class="flex items-center gap-2">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                ${icon}
            </svg>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 100);

    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 3000);
}

function updateDateRangeText() {
    const startDate = document.getElementById('start-date') ? document.getElementById('start-date').value : '';
    const endDate = document.getElementById('end-date') ? document.getElementById('end-date').value : '';
    const dateRangeText = document.getElementById('date-range-text');

    if (dateRangeText) {
        if (startDate && endDate) {
            dateRangeText.textContent = `${startDate} - ${endDate}`;
        } else {
            dateRangeText.textContent = 'Pilih Rentang Waktu';
        }
    }
}

function initializeDatePicker() {
    const startContainer = document.querySelector('[data-litepicker-start]');
    const endContainer = document.querySelector('[data-litepicker-end]');
    
    if (!startContainer || !endContainer) {
        return;
    }

    if (!window.Litepicker) {
        console.error('Litepicker library not loaded');
        return;
    }

    const startDateInput = document.createElement('input');
    const endDateInput = document.createElement('input');
    startDateInput.type = 'hidden';
    endDateInput.type = 'hidden';
    startDateInput.id = 'start-date';
    endDateInput.id = 'end-date';
    startContainer.appendChild(startDateInput);
    endContainer.appendChild(endDateInput);

    startPickerInstance = new Litepicker({
        element: startDateInput,
        singleMode: true,
        format: 'YYYY-MM-DD',
        autoApply: true,
        inlineMode: true,
        parentEl: startContainer,
        setup: (picker) => {
            picker.on('selected', (date) => {
                startDateInput.value = date ? date.format('YYYY-MM-DD') : '';
                filterPapers();
                updateDateRangeText();
            });
        }
    });

    endPickerInstance = new Litepicker({
        element: endDateInput,
        singleMode: true,
        format: 'YYYY-MM-DD',
        autoApply: true,
        inlineMode: true,
        parentEl: endContainer,
        setup: (picker) => {
            picker.on('selected', (date) => {
                endDateInput.value = date ? date.format('YYYY-MM-DD') : '';
                filterPapers();
                updateDateRangeText();
            });
        }
    });

    updateDateRangeText();
}

function clearDatePicker() {
    if (startPickerInstance && endPickerInstance) {
        startPickerInstance.clearSelection();
        endPickerInstance.clearSelection();
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        filterPapers();
        updateDateRangeText();
    }
}

function showDeleteConfirmation(paperId, paperTitle) {
    const modal = document.createElement('div');
    modal.id = 'delete-confirmation-modal';
    modal.className = 'fixed inset-0 z-50 overflow-y-auto';
    modal.innerHTML = `
        <div class="fixed inset-0 bg-gray-700/50" onclick="closeDeleteModal()"></div>
        
        <div class="relative min-h-screen flex items-center justify-center p-4">
            <div class="relative bg-gray-50 rounded-2xl max-w-xl w-full p-8" onclick="event.stopPropagation()">
                
                <div class="space-y-6">
                    <p class="text-xl md:text-2xl font-semibold text-center text-gray-900">Konfirmasi Penghapusan</p>
                    
                    <div class="text-center">
                        <p class="text-base md:text-lg text-gray-700 mb-4">
                            Apakah Anda yakin ingin menghapus karya ilmiah berikut dari daftar simpanan?
                        </p>
                        <p class="text-sm md:text-base font-medium text-gray-900 bg-gray-200 p-3 rounded-xl">
                            "${paperTitle}"
                        </p>
                        <p class="text-sm text-gray-600 mt-3">
                            Tindakan ini tidak dapat dibatalkan.
                        </p>
                    </div>
                </div>

                <div class="flex justify-between mt-8 w-full gap-4">
                    <button type="button"
                        id="cancel-delete-btn"
                        class="flex-1 px-6 py-3 text-gray-700 bg-gray-200 hover:bg-gray-300 font-medium rounded-xl text-base transition-colors">
                        Batal
                    </button>
                    
                    <button type="button"
                        id="confirm-delete-btn"
                        data-paper-id="${paperId}"
                        class="flex-1 px-6 py-3 text-white bg-red-600 hover:bg-red-700 font-medium rounded-xl text-base transition-colors">
                        Hapus Karya Ilmiah
                    </button>
                </div>

                <button 
                    onclick="closeDeleteModal()"
                    class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);

    // Add event listeners
    document.getElementById('cancel-delete-btn').addEventListener('click', closeDeleteModal);
    
    document.getElementById('confirm-delete-btn').addEventListener('click', () => {
        removePaper(paperId);
        closeDeleteModal();
    });

    // Close modal with Escape key
    document.addEventListener('keydown', handleEscapeKey);
}

function closeDeleteModal() {
    const modal = document.getElementById('delete-confirmation-modal');
    if (modal) {
        modal.remove();
        document.removeEventListener('keydown', handleEscapeKey);
    }
}

function handleEscapeKey(event) {
    if (event.key === 'Escape') {
        closeDeleteModal();
    }
}

function filterPapers() {
    const startDate = document.getElementById('start-date') ? document.getElementById('start-date').value : '';
    const endDate = document.getElementById('end-date') ? document.getElementById('end-date').value : '';
    const searchQuery = document.getElementById('search-input') ? document.getElementById('search-input').value.toLowerCase() : '';
    const container = document.getElementById('papers-container');

    let filteredPapers = allPapers;

    if (searchQuery) {
        filteredPapers = filteredPapers.filter(paper =>
            paper.title.toLowerCase().includes(searchQuery) || (paper.abstract && paper.abstract.toLowerCase().includes(searchQuery))
        );
    }

    if (startDate && endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);

        if (start > end) {
            container.innerHTML = `
                <div class="bg-red-100 p-4 rounded-lg text-red-700">
                    Tanggal awal tidak boleh lebih besar dari tanggal akhir.
                </div>
            `;
            return;
        }

        filteredPapers = filteredPapers.filter(paper => {
            const savedAt = new Date(paper.saved_at);
            return savedAt >= start && savedAt <= end;
        });
    }

    renderPapers(filteredPapers);
}

function renderPapers(papers) {
    const container = document.getElementById('papers-container');
    const totalPapers = papers.length;
    const totalPages = Math.ceil(totalPapers / papersPerPage);
    const startIndex = (currentPage - 1) * papersPerPage;
    const endIndex = startIndex + papersPerPage;
    const papersOnPage = papers.slice(startIndex, endIndex);

    if (!papersOnPage.length) {
        container.innerHTML = `
            <div class="bg-white rounded-lg shadow-md p-8 text-center mt-6">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                </svg>
                <h3 class="text-lg font-medium text-gray-900 mb-2">Tidak ada hasil ditemukan</h3>
                <p class="text-gray-600">Coba ubah rentang tanggal atau kata kunci pencarian Anda.</p>
            </div>
        `;
        return;
    }

    const groupedPapers = groupBy(papersOnPage, paper => {
        const date = new Date(paper.saved_at);
        const month = INDONESIAN_MONTHS[date.getMonth() + 1];
        return `Disimpan pada ${month} ${date.getFullYear()}`;
    });

    const currentPath = window.currentPath || '';
    let html = '';
    for (const [grouper, papers] of Object.entries(groupedPapers)) {
        html += `
            <div class="mb-8">
                <h2 class="text-xl font-bold text-gray-700 border-b-2 border-gray-200 pb-2 mb-4">${grouper}</h2>
                <div class="grid gap-6
                      [&_.bg-color]:bg-white
                      [&_.bg-color-author]:bg-gray-100
                      [&_.paper-title]:text-base lg:[&_.paper-title]:text-[25px]
                      [&_.paper-authors]:text-sm md:[&_.paper-authors]:text-base
                      [&_.paper-date]:text-sm md:[&_.paper-date]:text-base
                      [&_.paper-abstract]:text-sm md:[&_.paper-abstract]:text-base
                    ">
        `;
        papers.forEach(paper => {
            const authors = paper.authors;
            const remainingAuthors = authors.length > 3 ? authors.length - 3 : 0;
            const displayedAuthors = authors.slice(0, 3);
            html += `
                <div class="timeline-item pl-4 border-l-2 border-blue-500 relative group">
                    <div class="p-6 bg-color rounded-xl">
                        <a href="/papers/detail/${paper.paperId}>" class="paper-title line-clamp-2 md:line-clamp-3 text-justify font-semibold text-[#4787FA] no-underline hover:underline hover:cursor-pointer">${paper.title}</a>
                        <div class="flex items-center gap-2 mt-2 mb-1">
                            ${displayedAuthors.map(author => `
                                <span class="paper-authors max-w-[10ch] line-clamp-1 md:line-clamp-2 md:max-w-full px-3 py-1 text-[#4787FA] rounded-md bg-color-author">${author}</span>
                            `).join('')}
                            ${remainingAuthors > 0 ? `
                                <span class="paper-authors px-3 py-1 ${currentPath === '/access-history-recommendation/' ? 'bg-white' : 'bg-gray-100'} text-[#4787FA] rounded-md">
                                    <span class="md:hidden">+${remainingAuthors}</span>
                                    <span class="hidden md:inline">+${remainingAuthors} penulis</span>
                                </span>
                            ` : ''}
                            <span class="paper-date text-gray-800">${paper.formatted_publication_date || paper.year}</span>
                        </div>
                        <p class="paper-abstract text-gray-800 mt-2 text-justify line-clamp-3">${paper.abstract}</p>
                    </div>
                    <button class="remove-paper-btn absolute top-4 right-4 p-2 bg-white rounded-full text-gray-400 hover:bg-red-50 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                            data-paper-id="${paper.paperId}" data-paper-title="${paper.title}" title="Hapus dari simpanan">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
            `;
        });
        html += `</div></div>`;
    }

    if (totalPages > 1) {
        html += `
            <div class="pagination-container mt-10 flex justify-start items-center gap-2 font-semibold">
                <button class="pagination-btn px-4 py-2 bg-white border border-gray-300 rounded hover:bg-gray-100 cursor-pointer ${currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}" data-page="${currentPage - 1}" title="Halaman Sebelumnya" ${currentPage === 1 ? 'disabled' : ''}>
                    <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd" />
                    </svg>
                </button>
        `;
        const pageRange = getElidedPageRange(currentPage, totalPages);
        pageRange.forEach(num => {
            if (num === '...') {
                html += `<span class="px-4 py-2 border border-transparent text-gray-500">...</span>`;
            } else if (num === currentPage) {
                html += `<span class="px-4 py-2 bg-blue-100 text-blue-600 border border-blue-500 rounded z-10">${num}</span>`;
            } else {
                html += `<button class="pagination-btn px-4 py-2 bg-white border border-gray-300 rounded hover:bg-gray-100 cursor-pointer" data-page="${num}">${num}</button>`;
            }
        });
        html += `
                <button class="pagination-btn px-4 py-2 bg-white border border-gray-300 rounded hover:bg-gray-100 cursor-pointer ${currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : ''}" data-page="${currentPage + 1}" title="Halaman Berikutnya" ${currentPage === totalPages ? 'disabled' : ''}>
                    <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010-1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
                    </svg>
                </button>
            </div>
        `;
    }

    container.innerHTML = html;
}

function changePage(page) {
    const totalPages = Math.ceil(allPapers.length / papersPerPage);
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        filterPapers();
    }
}

function getElidedPageRange(currentPage, totalPages) {
    const delta = 2;
    const range = [];
    const rangeWithDots = [];
    let l;

    range.push(1);
    for (let i = currentPage - delta; i <= currentPage + delta; i++) {
        if (i > 1 && i < totalPages) {
            range.push(i);
        }
    }
    if (totalPages > 1) {
        range.push(totalPages);
    }

    for (let i of range) {
        if (l) {
            if (i - l === 2) {
                rangeWithDots.push(l + 1);
            } else if (i - l !== 1) {
                rangeWithDots.push('...');
            }
        }
        rangeWithDots.push(i);
        l = i;
    }

    return rangeWithDots;
}

function groupBy(array, keyFn) {
    return array.reduce((result, item) => {
        const key = keyFn(item);
        result[key] = result[key] || [];
        result[key].push(item);
        return result;
    }, {});
}

function removePaper(paperId) {
    fetch('/remove-paper/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ paperId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Karya ilmiah berhasil dihapus', 'success');
            allPapers = allPapers.filter(paper => paper.paperId !== paperId);
            filterPapers();
        } else {
            showNotification(data.error || 'Gagal menghapus karya ilmiah', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Terjadi kesalahan jaringan. Silakan coba lagi.', 'error');
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initializeDatePicker();
    
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', filterPapers);
    }
    
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.pagination-btn');
        if (btn && !btn.disabled) {
            const page = parseInt(btn.dataset.page);
            changePage(page);
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.remove-paper-btn');
        if (btn) {
            const paperId = btn.dataset.paperId;
            const paperTitle = btn.dataset.paperTitle;
            showDeleteConfirmation(paperId, paperTitle);
        }
    });

    const filterForm = document.getElementById('filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            filterPapers();
        });
    }

    filterPapers();
});

window.clearDatePicker = clearDatePicker;