from django_unicorn.components import UnicornView
import logging
import random
from app.services.neo4j_handler_services import Neo4jHandler
from app.services.paper_processor_services import PaperProcessor

logger = logging.getLogger(__name__)

class SearchResultView(UnicornView):
    papers = []
    query = ""
    start_date = ""
    end_date = ""
    page = 1
    results_count = 0
    is_loading = True
    error = ""
    paginator = None

    def mount(self):
        self.query = self.request.GET.get('query', '').strip()
        self.page = int(self.request.GET.get('page', '1'))
        logger.info(f"Component SearchResultView Mounted for query: '{self.query}'")
        self.cleanup_old_sessions()
            
        session_key = f"pure_search_{self.query}"
        if self.request.session.get(session_key):
            self.is_loading = False
            self.load_from_session()
        else:
            self.is_loading = True
            
    def get_pagination_range(self, total_pages, current_page, on_each_side=1, on_ends=1):
        if total_pages <= (on_each_side + on_ends) * 2 + 1:
            return list(range(1, total_pages + 1))

        pages = []
        for i in range(current_page - on_each_side, current_page + on_each_side + 1):
            if 1 <= i <= total_pages:
                pages.append(i)
        
        for i in range(1, on_ends + 1):
            if i not in pages:
                pages.append(i)
        
        for i in range(total_pages - on_ends + 1, total_pages + 1):
            if i not in pages:
                pages.append(i)
        
        pages.sort()
        
        result = []
        last_page = 0
        for page in pages:
            if last_page != 0 and page - last_page > 1:
                result.append('...')
            result.append(page)
            last_page = page
            
        return result
    
    def cleanup_old_sessions(self):
        session_keys = [key for key in self.request.session.keys() if key.startswith('pure_search_')]
        current_key = f"pure_search_{self.query}"
        
        for key in session_keys:
            if key != current_key:
                logger.info(f"Menghapus session lama: {key}")
                del self.request.session[key]
                status_key = f"search_status_{key.replace('pure_search_', '')}"
                if status_key in self.request.session:
                    del self.request.session[status_key]
        self.request.session.modified = True
        
    def set_dates_and_reload(self, start_date, end_date):
        self.error = ""
        self.is_loading = True
        self.page = 1
        self.start_date = start_date
        self.end_date = end_date
        self.load_from_session()
        
    def load_from_session(self):
        try:
            session_key = f"pure_search_{self.query}"
            all_papers = self.request.session.get(session_key, [])
            logger.info(f"Papers dari sesi: {len(all_papers)} untuk query: '{self.query}'")
            
            if not all_papers:
                self.error = "Tidak ada hasil ditemukan untuk kueri Anda."
                self.is_loading = False
                return

            filtered_papers = PaperProcessor.filter_papers_by_year(all_papers, self.start_date, self.end_date)
            self.results_count = len(filtered_papers)
            
            # Pagination
            per_page = 10
            total_pages = max(1, (self.results_count + per_page - 1) // per_page)
            self.page = min(max(1, self.page), total_pages)
            start_idx = (self.page - 1) * per_page
            end_idx = start_idx + per_page
            self.papers = filtered_papers[start_idx:end_idx]
            self.paginator = {
                'num_pages': total_pages,
                'page_range': self.get_pagination_range(total_pages, self.page),
                'has_previous': self.page > 1,
                'has_next': self.page < total_pages,
                'previous_page_number': self.page - 1,
                'next_page_number': self.page + 1,
                'number': self.page
            }
        except Exception as e:
            logger.error(f"Error loading from session: {str(e)}", exc_info=True)
            self.error = f"Error loading results: {str(e)}"
        finally:
            self.is_loading = False
            logger.info(f"is_loading diatur ke: {self.is_loading}")
            
    def load_page(self, page):
        self.is_loading = True
        logger.info(f"Memuat halaman {page}...")
        try:
            self.page = int(page)
            self.load_from_session()
        except Exception as e:
            logger.error(f"Error pada paginasi: {e}", exc_info=True)
            self.error = "Gagal memuat halaman."
            self.is_loading = False