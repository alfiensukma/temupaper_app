from django_unicorn.components import UnicornView
from django.core.paginator import Paginator
from app.utils.neo4j_connection import Neo4jConnection
from app.utils.parse_indonesian_date import format_date_to_indonesian
import logging

logger = logging.getLogger(__name__)

class AccessHistoryView(UnicornView):
    papers = []
    pagination_data = None
    _all_papers = []
    _page = 1
    error = None
    
    def mount(self):
        user_id = self.request.session.get('user_id')
        if not user_id:
            self.error = "Sesi pengguna tidak valid. Silakan login kembali."
            return
        
        driver = None
        try:
            neo4j_connection = Neo4jConnection()
            driver = neo4j_connection.get_driver()

            with driver.session() as session:
                result = session.run("""
                    MATCH (u:User {userId: $userId})-[:HAS_READ]->(n:Paper)-[r:HIGHEST_SIMILAR]->(p:Paper)
                    WHERE NOT (u)-[:HAS_READ]->(p)
                    OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                    RETURN 
                        p.title AS title,
                        p.paperId as paperId,
                        p.abstract as abstract, 
                        p.publicationDate AS date,
                        p.year AS year,
                        p.pagerank as pagerank,
                        r.score as score,
                        collect(DISTINCT author.name) AS authors
                    ORDER BY r.score DESC, p.pagerank DESC, p.publicationDate DESC
                    """,
                    userId=user_id
                )
                
                papers_raw = list(result)
            
            processed_papers = []
            for record in papers_raw:
                paper = dict(record)
                
                paper["date"] = format_date_to_indonesian(
                    paper.get("date"), 
                    fallback_year=paper.get("year", "N/A")
                )
                processed_papers.append(paper)
            self._all_papers = processed_papers
            self.paginate()

        except Exception as e:
            logger.error(f"Error di AccessHistoryView: {e}", exc_info=True)
            self._error = "Gagal memuat rekomendasi."
        finally:
            if driver:
                driver.close()

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

    def paginate(self):
        if not self._all_papers:
            self.papers = []
            self.pagination_data = None
            return

        paginator = Paginator(self._all_papers, 10)
        total_pages = paginator.num_pages
        self._page = min(max(1, self._page), total_pages)
        page_obj = paginator.get_page(self._page)
        self.papers = list(page_obj.object_list)
        self.pagination_data = {
            'num_pages': total_pages,
            'page_range': self.get_pagination_range(total_pages, self._page),
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'number': self._page,
            'ELLIPSIS': '...',
        }

    def load_page(self, page_number):
        self._page = int(page_number)
        self.paginate()
