document.addEventListener('alpine:init', () => {
    Alpine.data('searchResult', () => ({
        query: '',
        papers: [],
        displayedPapers: [],
        startYear: '',
        endYear: '',
        selectedRank: '',
        isLoading: false,
        error: '',
        yearFilterError: '',
        paginator: {
            currentPage: 1,
            totalPages: 1,
            perPage: 10
        },
        _allPapersCache: [],
        _filteredPapersCache: [],
        isYearFilterOpen: false,
        years: [],
        ranks: [],

        init(query) {
            // Muat filter dari sessionStorage agar tetap ada saat halaman dimuat ulang
            this.startYear = sessionStorage.getItem('startYear') || '';
            this.endYear = sessionStorage.getItem('endYear') || '';
            this.selectedRank = sessionStorage.getItem('selectedRank') || '';

            this.query = query && query !== 'undefined' && query.trim() ? query : (new URLSearchParams(window.location.search).get('query')?.trim() || '');
            if (this.query) {
                this.isLoading = true;
                this.fetchPapers();
            } else {
                this.isLoading = false;
                this.error = 'Kueri pencarian tidak ditemukan. Silakan masukkan kueri.';
            }
            const debounce = (func, wait) => {
                let timeout;
                return (...args) => {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => func.apply(this, args), wait);
                };
            };
            window.addEventListener('scroll', debounce(() => {
                const header = document.querySelector('.search-header');
                const filterContainer = document.querySelector('.filter-container');
                if (header && filterContainer) {
                    const scrollPosition = window.scrollY;
                    if (scrollPosition > 50) {
                        header.style.opacity = '0';
                        header.setAttribute('aria-hidden', 'true');
                        filterContainer.classList.add('sticky');
                    } else {
                        header.style.opacity = 1 - scrollPosition / 50;
                        header.removeAttribute('aria-hidden');
                        filterContainer.classList.remove('sticky');
                    }
                }
            }, 10));
        },

        validateYears() {
            if (this.startYear && this.endYear && parseInt(this.startYear) > parseInt(this.endYear)) {
                this.yearFilterError = 'Tahun awal tidak boleh lebih besar dari tahun akhir';
                this.isYearFilterOpen = true;
            } else {
                this.yearFilterError = '';
                sessionStorage.setItem('startYear', this.startYear);
                sessionStorage.setItem('endYear', this.endYear);
            }
        },

        async fetchPapers() {
            if (!this.query) {
                this.isLoading = false;
                this.error = 'Kueri pencarian tidak valid.';
                return;
            }

            this.isLoading = true;
            this.error = '';
            this.yearFilterError = '';
            const sessionKey = `pure_search_${this.query}`;

            // Hapus cache client-side lama hanya jika kueri berubah
            const lastQuery = sessionStorage.getItem('last_search_query');
            if (lastQuery && lastQuery !== this.query) {
                this.clearOldSessions(sessionKey);
                sessionStorage.setItem('last_search_query', this.query);
            }

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            if (!csrfToken) {
                this.error = 'Konfigurasi CSRF tidak ditemukan. Silakan muat ulang halaman.';
                this.isLoading = false;
                return;
            }

            try {
                const url = new URL('/search-api/', window.location.origin);
                url.searchParams.append('query', this.query);
                if (this.startYear) url.searchParams.append('start_year', this.startYear);
                if (this.endYear) url.searchParams.append('end_year', this.endYear);
                if (this.selectedRank) url.searchParams.append('rank', this.selectedRank);

                const response = await fetch(url, {
                    method: 'GET',
                    headers: { 'Accept': 'application/json', 'X-CSRFToken': csrfToken }
                });
                if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                const data = await response.json();

                if (data.papers && data.papers.length > 0) {
                    this._allPapersCache = data.papers.map(paper => ({
                        paperId: paper.paperId || '',
                        title: paper.title || 'Untitled',
                        abstract: paper.abstract || '',
                        citation_count: paper.citation_count || 0,
                        similarity: paper.similarity || 0,
                        authors: paper.authors || [],
                        date: paper.date || '',
                        year: paper.year || '',
                        is_seed: paper.is_seed || false,
                        rank: paper.rank || 'Tidak Teridentifikasi'
                    }));
                    this.years = data.years || [];
                    this.ranks = data.ranks || ['Semua Peringkat'];
                    this.papers = [...this._allPapersCache];
                    this._filteredPapersCache = [...this._allPapersCache];
                    sessionStorage.setItem(sessionKey, JSON.stringify({
                        papers: this._allPapersCache,
                        years: this.years,
                        ranks: this.ranks
                    }));
                    this.renderPapers('');
                } else {
                    this.papers = [];
                    this._filteredPapersCache = [];
                    this.years = data.years || [];
                    this.ranks = data.ranks || ['Semua Peringkat'];
                    this.renderPapers(data.message?.includes('filter') ? 'filter' : 'notfound-query');
                }
            } catch (err) {
                this.error = `Terjadi kesalahan saat memuat data: ${err.message}`;
                this.papers = [];
                this._filteredPapersCache = [];
                this.years = [];
                this.ranks = ['Semua Peringkat'];
                this.renderPapers('notfound-query');
            } finally {
                this.isLoading = false;
            }
        },

        clearOldSessions(currentSessionKey) {
            Object.keys(sessionStorage).forEach(key => {
                if (key.startsWith('pure_search_') && key !== currentSessionKey) {
                    sessionStorage.removeItem(key);
                }
            });
        },

        applyFilter() {
            sessionStorage.setItem('startYear', this.startYear);
            sessionStorage.setItem('endYear', this.endYear);
            sessionStorage.setItem('selectedRank', this.selectedRank);
            this.fetchPapers();
        },

        resetFilter() {
            this.startYear = '';
            this.endYear = '';
            this.selectedRank = '';
            this.error = '';
            this.yearFilterError = '';
            this.isYearFilterOpen = false;
            sessionStorage.removeItem('startYear');
            sessionStorage.removeItem('endYear');
            sessionStorage.removeItem('selectedRank');
            this.fetchPapers();
        },

        renderPapers(context = '') {
            const container = document.getElementById('papers-container');
            if (!container) {
                return;
            }

            const totalPapers = this._filteredPapersCache.length;
            this.paginator.totalPages = Math.ceil(totalPapers / this.paginator.perPage);
            
            const startIndex = (this.paginator.currentPage - 1) * this.paginator.perPage;
            const endIndex = startIndex + this.paginator.perPage;
            this.displayedPapers = this._filteredPapersCache.slice(startIndex, endIndex);

            if (!this.displayedPapers.length) {
                if (context === 'notfound-query') {
                    container.innerHTML = `
                        <div class="text-center py-10 mt-16">
                            <p class="text-gray-600 text-xl font-semibold">Hasil tidak ditemukan</p>
                            <p class="text-gray-500 mt-2">Kueri pencarian '${this.query}' tidak menghasilkan artikel ilmiah apapun.</p>
                        </div>
                    `;
                } else if (context === 'filter') {
                    container.innerHTML = `
                        <div class="text-center py-10 mt-16">
                            <p class="text-gray-600 text-xl font-semibold">Hasil tidak ditemukan</p>
                            <p class="text-gray-500 mt-2">Tidak ada paper yang sesuai dengan filter yang dipilih.</p>
                        </div>
                    `;
                } else {
                    container.innerHTML = `
                        <div class="text-center py-10 mt-16">
                            <p class="text-gray-600 text-xl font-semibold">Hasil tidak ditemukan</p>
                            <p class="text-gray-500 mt-2">Kueri pencarian '${this.query}' tidak menghasilkan artikel ilmiah apapun.</p>
                        </div>
                    `;
                }
                this.updatePagination();
                return;
            }

            container.innerHTML = '';
            this.displayedPapers.forEach(paper => {
                const paperElement = document.createElement('div');
                paperElement.className = 'p-6 bg-white rounded-xl';
                
                const escapeHtml = (text) => {
                    const div = document.createElement('div');
                    div.textContent = text;
                    return div.innerHTML;
                };

                const displayRank = !paper.rank || paper.rank in ['-', '', null] ? 'Tidak Teridentifikasi' : paper.rank;

                paperElement.innerHTML = `
                    <a href="/papers/detail/${paper.paperId}/" class="paper-title line-clamp-2 md:line-clamp-3 text-justify font-semibold text-[#4787FA] no-underline hover:underline hover:cursor-pointer">${escapeHtml(paper.title)}</a>
                    <div class="flex items-center gap-2 mt-2 mb-1">
                        ${paper.authors.slice(0, 3).map(author => `
                            <span class="paper-authors max-w-[10ch] line-clamp-1 md:line-clamp-2 md:max-w-full px-3 py-0.5 text-[#4787FA] rounded-xl bg-blue-50">${escapeHtml(author)}</span>
                        `).join('')}
                        ${paper.authors.length > 3 ? `
                            <span class="paper-authors px-3 py-0.5 text-[#4787FA] rounded-xl bg-blue-50">
                                <span class="md:hidden">+${paper.authors.length - 3}</span>
                                <span class="hidden md:inline">+${paper.authors.length - 3} penulis</span>
                            </span>
                        ` : ''}
                        <span class="paper-date text-gray-800">${escapeHtml(paper.date || paper.year)}</span>
                        ${displayRank !== 'Tidak Teridentifikasi' ? `
                            <span class="px-2 py-1 text-xs bg-blue-50 text-blue-500 rounded-full">${escapeHtml(displayRank)}</span>
                        ` : ''}
                    </div>
                    <p class="paper-abstract text-gray-800 mt-2 text-justify line-clamp-3">${escapeHtml(paper.abstract)}</p>
                `;
                container.appendChild(paperElement);
            });
            
            this.updatePagination();
        },

        changePage(page) {
            const pageNum = parseInt(page);
            if (pageNum >= 1 && pageNum <= this.paginator.totalPages && pageNum !== this.paginator.currentPage) {
                this.paginator.currentPage = pageNum;
                this.renderPapers();
            }
        },

        updatePagination() {
            const paginationContainer = document.querySelector('.pagination-container');
            if (!paginationContainer) return;

            paginationContainer.innerHTML = '';

            if (this.paginator.totalPages <= 1) return;

            const paginationDiv = document.createElement('div');
            paginationDiv.className = 'mt-10 flex justify-start items-center gap-2 font-semibold';

            const prevBtn = document.createElement('span');
            const hasPrevious = this.paginator.currentPage > 1;
            
            if (hasPrevious) {
                prevBtn.className = 'pagination-btn px-4 py-2 bg-white border border-gray-300 rounded hover:bg-gray-100 cursor-pointer';
                prevBtn.title = 'Halaman Sebelumnya';
                prevBtn.addEventListener('click', () => {
                    this.changePage(this.paginator.currentPage - 1);
                });
            } else {
                prevBtn.className = 'pagination-btn px-4 py-2 bg-gray-100 text-gray-400 border border-gray-300 rounded cursor-not-allowed';
                prevBtn.title = 'Halaman Sebelumnya';
            }
            
            prevBtn.innerHTML = `
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd" />
                </svg>
            `;
            paginationDiv.appendChild(prevBtn);

            const pageRange = this.getElidedPageRange(this.paginator.currentPage, this.paginator.totalPages);
            
            pageRange.forEach(num => {
                if (num === '...') {
                    const ellipsis = document.createElement('span');
                    ellipsis.className = 'px-4 py-2 border border-transparent text-gray-500';
                    ellipsis.textContent = '...';
                    paginationDiv.appendChild(ellipsis);
                } else if (num === this.paginator.currentPage) {
                    const activePage = document.createElement('span');
                    activePage.className = 'px-4 py-2 bg-blue-100 text-blue-600 border border-blue-500 rounded z-10';
                    activePage.textContent = num;
                    paginationDiv.appendChild(activePage);
                } else {
                    const pageBtn = document.createElement('span');
                    pageBtn.className = 'pagination-btn px-4 py-2 bg-white border border-gray-300 rounded hover:bg-gray-100 cursor-pointer';
                    pageBtn.textContent = num;
                    pageBtn.addEventListener('click', () => {
                        this.changePage(num);
                    });
                    paginationDiv.appendChild(pageBtn);
                }
            });

            const nextBtn = document.createElement('span');
            const hasNext = this.paginator.currentPage < this.paginator.totalPages;
            
            if (hasNext) {
                nextBtn.className = 'pagination-btn px-4 py-2 bg-white border border-gray-300 rounded hover:bg-gray-100 cursor-pointer';
                nextBtn.title = 'Halaman Berikutnya';
                nextBtn.addEventListener('click', () => {
                    this.changePage(this.paginator.currentPage + 1);
                });
            } else {
                nextBtn.className = 'pagination-btn px-4 py-2 bg-gray-100 text-gray-400 border border-gray-300 rounded cursor-not-allowed';
                nextBtn.title = 'Halaman Berikutnya';
            }
            
            nextBtn.innerHTML = `
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
                </svg>
            `;
            paginationDiv.appendChild(nextBtn);

            paginationContainer.appendChild(paginationDiv);
        },

        getElidedPageRange(currentPage, totalPages) {
            const delta = 2;
            const range = [];
            const rangeWithDots = [];
            let l;

            range.push(1);
            for (let i = currentPage - delta; i <= currentPage + delta; i++) {
                if (i > 1 && i < totalPages) range.push(i);
            }
            if (totalPages > 1) range.push(totalPages);

            for (let i of range) {
                if (l) {
                    if (i - l === 2) rangeWithDots.push(l + 1);
                    else if (i - l !== 1) rangeWithDots.push('...');
                }
                rangeWithDots.push(i);
                l = i;
            }
            return rangeWithDots;
        }
    }));
});