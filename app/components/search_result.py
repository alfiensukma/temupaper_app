from django_unicorn.components import UnicornView
import logging
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
    state = ""

    def mount(self):
        try:
            new_query = self.request.GET.get('query', '').strip()
            self.state = self.request.GET.get('state', '')
            old_query = self.request.session.get('current_query', '')
            logger.info(f"Mounting SearchResultView: new_query={new_query}, old_query={old_query}, state={self.state}")
            self.is_loading = True
            if self.state != 'loaded' or new_query != old_query:
                keys_to_delete = [key for key in self.request.session.keys() 
                                if key.startswith('pure_search_') or 
                                key in ['current_query', 'query', 'start_date', 'end_date', 'page']]
                for key in keys_to_delete:
                    try:
                        del self.request.session[key]
                    except KeyError:
                        pass
                self.query = new_query
                self.papers = []
                self.results_count = 0
                self.start_date = ""
                self.end_date = ""
                self.page = 1
                self.error = ""
                self.paginator = None
                self.request.session['current_query'] = new_query
                self.request.session.modified = True
                logger.info(f"New query detected, reset state: query={new_query}")
                self.start_search()
            else:
                self.query = new_query
                self.start_date = str(self.request.session.get('start_date', ''))
                self.end_date = str(self.request.session.get('end_date', ''))
                self.page = int(self.request.session.get('page', '1'))
                logger.info(f"Loading from session: start_date={self.start_date}, end_date={self.end_date}, page={self.page}")
                self.load_from_session()
        except Exception as e:
            logger.error(f"Mount error: {str(e)}")
            self.error = f"Error saat inisialisasi: {str(e)}"
            self.is_loading = False

    def start_search(self):
        try:
            self.is_loading = True
            if not self.query:
                self.is_loading = False
                self.error = "Silakan masukkan kueri pencarian"
                logger.warning("Empty query provided")
                return
            neo4j_handler = Neo4jHandler()
            paper_id = None
            try:
                paper_id = neo4j_handler.create_search_node(self.query)
                graph_name = neo4j_handler.create_graph_projection()
                seed_paper_ids = neo4j_handler.find_seed_papers(paper_id)
                if not seed_paper_ids:
                    logger.warning("No seed papers found for query.")
                    self.is_loading = False
                    self.error = "Tidak ditemukan hasil untuk kueri Anda."
                    return
                knn_details, similar_results = neo4j_handler.find_similar_papers(seed_paper_ids)
                papers = PaperProcessor.process_search_results(knn_details, similar_results)
                if not papers:
                    logger.warning("No results after processing.")
                    self.is_loading = False
                    self.error = "Tidak ditemukan hasil untuk kueri Anda."
                    return
                session_key = f"pure_search_{self.query}"
                self.request.session[session_key] = papers
                self.request.session['query'] = self.query
                self.request.session['current_query'] = self.query
                self.request.session.modified = True
                self.load_from_session()
            except Exception as e:
                logger.error(f"Error during search: {str(e)}")
                self.is_loading = False
                self.error = f"Terjadi kesalahan saat pencarian: {str(e)}"
            finally:
                if paper_id:
                    neo4j_handler.delete_query_node(paper_id)
                neo4j_handler.close()
        except Exception as e:
            logger.error(f"Start search error: {str(e)}")
            self.is_loading = False
            self.error = f"Error saat memulai pencarian: {str(e)}"

    def load_from_session(self):
        try:
            self.is_loading = True
            session_key = f"pure_search_{self.query}"
            papers = self.request.session.get(session_key, [])
            if not papers:
                self.papers = []
                self.results_count = 0
                self.is_loading = False
                logger.info("No papers found in session")
                return
            filtered_papers = PaperProcessor.filter_papers_by_year(papers, self.start_date, self.end_date)
            self.results_count = len(filtered_papers)
            per_page = 10
            total_pages = (self.results_count + per_page - 1) // per_page
            self.page = min(max(1, self.page), total_pages)
            start_idx = (self.page - 1) * per_page
            end_idx = start_idx + per_page
            self.papers = filtered_papers[start_idx:end_idx]
            self.paginator = {
                'num_pages': total_pages,
                'page_range': list(range(1, total_pages + 1)),
                'has_previous': self.page > 1,
                'has_next': self.page < total_pages,
                'previous_page_number': self.page - 1,
                'next_page_number': self.page + 1,
                'number': self.page
            }
            self.is_loading = False
            logger.info(f"Loaded papers: count={self.results_count}, page={self.page}, total_pages={total_pages}")
        except Exception as e:
            logger.error(f"Error loading from session: {str(e)}")
            self.error = f"Error loading results: {str(e)}"
            self.is_loading = False
            
    def load_page(self, page):
        try:
            self.is_loading = True 
            page = int(page)
            self.page = page
            self.request.session['page'] = page
            self.request.session.modified = True
            self.load_from_session()
        except Exception as e:
            logger.error(f"Error loading page {page}: {str(e)}")
            self.error = f"Error saat memuat halaman: {str(e)}"