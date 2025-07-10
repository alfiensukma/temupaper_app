from django_unicorn.components import UnicornView
from django.core.paginator import Paginator
from neomodel import db
import logging
from app.models import User
from app.utils.parse_indonesian_date import format_date_to_indonesian

logger = logging.getLogger(__name__)

class PeerInstitutionView(UnicornView):
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
        self.get_peer_recommendations(user_id)

    def get_peer_recommendations(self, user_id):
        try:
            current_user = User.nodes.get(userId=user_id)
            institution_node = current_user.affiliated_with.get_or_none()
            if not institution_node:
                self._all_papers = []
                self.paginate()
                return

            institutionId = institution_node.institutionId
            query = """
                MATCH (pt:Institution {institutionId: $institutionId})<-[:AFFILIATED_WITH]-(u:User)-[:HAS_READ]->(p:Paper)
                WHERE NOT EXISTS {
                  MATCH (currentUser:User {userId: $userId})-[:HAS_READ]->(p)
                }
                WITH p, count(u) AS jumlahPembaca,
                    CASE
                      WHEN p.publicationDate IS NOT NULL AND p.publicationDate CONTAINS '-' 
                        THEN date(left(p.publicationDate, 10))
                      WHEN p.publicationDate IS NOT NULL AND p.publicationDate CONTAINS '/' 
                        THEN date(datetime({epochMillis: apoc.date.parse(split(p.publicationDate, ' ')[0], 'ms', 'M/d/yyyy')}))
                      ELSE null
                    END AS normalizedDate
                ORDER BY jumlahPembaca DESC, normalizedDate DESC, p.year DESC
                LIMIT 20
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                RETURN 
                    p.title AS title,
                    p.paperId as paperId,
                    p.abstract as abstract, 
                    jumlahPembaca,
                    p.publicationDate AS date,
                    p.year AS year,
                    p.pagerank as pagerank,
                    collect(DISTINCT author.name) AS authors
            """
            params = {'institutionId': institutionId, 'userId': user_id}
            results, meta = db.cypher_query(query, params)
            papers_raw = [dict(zip(meta, row)) for row in results]
            
            processed_papers = []
            for record in papers_raw:
                record["date"] = format_date_to_indonesian(
                    record.get("date"), 
                    fallback_year=record.get("year", "N/A")
                )
                processed_papers.append(record)
                
            self._all_papers = processed_papers
            self.paginate()

        except Exception as e:
            logger.error(f"Error di PeerInstitutionView: {e}", exc_info=True)
            self.error = "Gagal memuat rekomendasi rekan institusi."

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
