from django_unicorn.components import UnicornView
from neo4j.exceptions import ServiceUnavailable
from app.services.search_recommendation_services import Neo4jHandler
from app.services.paper_processor_services import PaperProcessor
from django.core.paginator import Paginator
import logging

logger = logging.getLogger(__name__)

class SearchResultView:
    def __init__(self):
        self.is_loading = True
        self.error = None
        self.error_message = None
        self.query = ''
        self.start_date = ''
        self.end_date = ''
        self.journal_rank = 'Semua Peringkat'
        self.selected_rank = 'Semua Peringkat'
        self.page = 1
        self.papers = []
        self.paginator = None
        self._all_papers_cache = []

    def mount(self):
        self.query = self.request.GET.get('query', '').strip()
        self.page = int(self.request.GET.get('page', '1'))
        logger.info(f"Component SearchResultView Mounted. Memulai pencarian untuk '{self.query}'...")
        self.perform_initial_search()

    def perform_initial_search(self):
        session_key = f"pure_search_{self.query}"
        handler = None

        try:
            cached_papers = self.request.session.get(session_key)
            if cached_papers is not None:
                logger.info(f"Data ditemukan di session untuk query: '{self.query}'")
                self._all_papers_cache = cached_papers
            else:
                logger.info(f"Melakukan pencarian baru di dalam mount untuk: '{self.query}'")
                handler = Neo4jHandler()
                papers_data = []
                paper_id = None
                try:
                    paper_id = handler.create_search_node(self.query)
                    handler.create_graph_projection()
                    seed_paper_ids = handler.find_seed_papers(paper_id)
                    
                    if seed_paper_ids:
                        knn_details, similar_results = handler.find_similar_papers(seed_paper_ids)
                        papers_data = PaperProcessor.process_search_results(knn_details, similar_results)

                finally:
                    if paper_id: handler.delete_query_node(paper_id)
                    if hasattr(handler, 'graph_name') and handler.graph_name: handler.drop_graph()

                self.request.session[session_key] = papers_data
                self._all_papers_cache = papers_data
            
            self.apply_filters_and_paginate()

        except ServiceUnavailable:
            self.error = "Tidak dapat terhubung ke database. Pastikan layanan Neo4j sedang berjalan."
            logger.error(self.error, exc_info=True)
        except Exception as e:
            self.error = "Terjadi kesalahan pada server saat melakukan pencarian."
            logger.error(f"Error tidak terduga di mount: {str(e)}", exc_info=True)
        finally:
            self.is_loading = False
            if handler:
                handler.close()

    def apply_filters_and_paginate(self):
        papers_to_filter = self._all_papers_cache
        
        if self.start_date and self.end_date:
            try:
                start_year = int(self.start_date)
                end_year = int(self.end_date)
                if start_year <= end_year:
                    papers_to_filter = PaperProcessor.filter_papers_by_year(papers_to_filter, self.start_date, self.end_date)
                    logger.info(f"After year filter: {len(papers_to_filter)} papers")
                else:
                    self.error_message = "Tahun awal tidak boleh lebih besar dari tahun akhir."
                    logger.warning(f"Invalid year range: start_year={start_year} > end_year={end_year}")
                    return
            except ValueError:
                self.error_message = "Format tahun tidak valid."
                logger.error(f"Invalid year values: start_date={self.start_date}, end_date={self.end_date}")
                return
        else:
            logger.info("No year filter applied")

        if self.journal_rank != "Semua Peringkat":
            papers_to_filter = PaperProcessor.filter_papers_by_quartile(papers_to_filter, self.journal_rank)
            logger.info(f"After quartile filter: {len(papers_to_filter)} papers for quartile: {self.journal_rank}")
        else:
            logger.info("No quartile filter applied")

        paginator = Paginator(papers_to_filter, 10)
        self.page = min(max(1, self.page), paginator.num_pages)
        page_obj = paginator.get_page(self.page)
        self.papers = page_obj.object_list
        
        if paginator.num_pages > 0:
            self.paginator = {
                'num_pages': paginator.num_pages,
                'number': self.page,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
                'page_range': self.get_pagination_range(paginator.num_pages, self.page),
            }
        else:
            self.paginator = None

    def apply_filter(self):
        self.is_loading = True
        try:
            self.page = 1
            self.error_message = None
            logger.info(f"Applying filter: start_date={self.start_date}, end_date={self.end_date}")
            self.apply_filters_and_paginate()
        finally:
            self.is_loading = False

    def set_dates_and_reload(self, start_date, end_date):
        self.is_loading = True
        try:
            self.start_date = start_date
            self.end_date = end_date
            self.page = 1
            self.error_message = None
            logger.info(f"Setting dates: start_date={start_date}, end_date={end_date}")
            self.apply_filters_and_paginate()
        finally:
            self.is_loading = False

    def clear_date_filter(self):
        self.is_loading = True
        try:
            self.start_date = ''
            self.end_date = ''
            self.page = 1
            self.error_message = None
            logger.info("Clearing date filter")
            self.apply_filters_and_paginate()
        finally:
            self.is_loading = False

    def set_rank(self, rank):
        self.is_loading = True
        try:
            self.journal_rank = rank
            self.selected_rank = rank
            self.page = 1
            logger.info(f"Setting journal rank: {rank}")
            self.apply_filters_and_paginate()
        finally:
            self.is_loading = False

    def clear_filter(self):
        self.is_loading = True
        try:
            self.journal_rank = 'Semua Peringkat'
            self.selected_rank = 'Semua Peringkat'
            self.page = 1
            logger.info("Clearing journal rank filter")
            self.apply_filters_and_paginate()
        finally:
            self.is_loading = False

    def load_page(self, page_number):
        if page_number:
            self.is_loading = True
            try:
                self.page = int(page_number)
                self.apply_filters_and_paginate()
            finally:
                self.is_loading = False
            
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