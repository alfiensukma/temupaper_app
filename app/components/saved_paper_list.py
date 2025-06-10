from django_unicorn.components import UnicornView
from datetime import datetime
from itertools import groupby
from django.core.paginator import Paginator
from app.models import User, Paper
from app.utils.parse_indonesian_date import format_date_to_indonesian
import logging

logger = logging.getLogger(__name__)

INDONESIAN_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

class SavedPaperListView(UnicornView):
    search_query = ""
    start_date = ""
    end_date = ""
    papers_by_date: list = []
    pagination_data = None
    results_count = 0
    error = None
    _all_papers: list = []
    _page = 1
    total_paper_count = 0

    def mount(self):
        user_id = self.request.session.get('user_id')
        if not user_id:
            self.error = "Sesi pengguna tidak valid. Silakan login kembali."
            return

        try:
            user = User.nodes.get(userId=user_id)
            all_saved_papers = user.saves_papers.all()

            processed_papers = []
            for paper in all_saved_papers:
                rel = user.saves_papers.relationship(paper)
                saved_at = rel.saved_at if hasattr(rel, 'saved_at') else datetime.now()
                
                if isinstance(saved_at, float):
                    saved_at = datetime.fromtimestamp(saved_at)

                paper_data = {
                    "paperId": paper.paperId,
                    "title": paper.title or "Judul Tidak Tersedia",
                    "abstract": paper.abstract or "",
                    "year": paper.year,
                    "authors": [author.name for author in paper.authored_by.all()],
                    "saved_at": saved_at,
                    "publicationDate": paper.publicationDate,
                }
                processed_papers.append(paper_data)

            self._all_papers = sorted(processed_papers, key=lambda p: p['saved_at'], reverse=True)
            self.total_paper_count = len(self._all_papers)
            self.filter_and_paginate()
        except Exception as e:
            logger.error(f"Error mounting SavedPaperListView: {e}", exc_info=True)
            self.error = "Gagal memuat daftar karya ilmiah tersimpan."

    def filter_and_paginate(self):
        filtered_papers = self._all_papers
        if self.search_query:
            query = self.search_query.lower()
            filtered_papers = [
                p for p in filtered_papers 
                if query in p['title'].lower() or (p['abstract'] and query in p['abstract'].lower())
            ]
        
        if self.start_date:
            start_dt = datetime(int(self.start_date), 1, 1)
            filtered_papers = [p for p in filtered_papers if p['saved_at'].replace(tzinfo=None) >= start_dt]
        if self.end_date:
            end_dt = datetime(int(self.end_date), 12, 31)
            filtered_papers = [p for p in filtered_papers if p['saved_at'].replace(tzinfo=None) <= end_dt]

        self.results_count = len(filtered_papers)
        
        paginator = Paginator(filtered_papers, 5)
        self._page = min(max(1, self._page), paginator.num_pages)
        page_obj = paginator.get_page(self._page)
        
        papers_on_page = list(page_obj.object_list)
        for paper in papers_on_page:
            saved_at_datetime = paper['saved_at']
            month_number = saved_at_datetime.month
            indonesian_month_name = INDONESIAN_MONTHS[month_number]
            paper['formatted_date'] = f"Disimpan pada {indonesian_month_name} {saved_at_datetime.year}"
            paper['formatted_publication_date'] = format_date_to_indonesian(paper.get("publicationDate"), paper.get("year"))

        grouped_papers = []
        for key, group in groupby(papers_on_page, key=lambda p: p['formatted_date']):
            grouped_papers.append({"grouper": key, "list": list(group)})
        self.papers_by_date = grouped_papers
        
        self.pagination_data = {
            'number': self._page, 'num_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(), 'has_next': page_obj.has_next(),
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'page_range': [i for i in paginator.get_elided_page_range(self._page)],
            'ELLIPSIS': '...',
        }

    def updated_search_query(self, value):
        self._page = 1
        self.filter_and_paginate()

    def set_dates_and_reload(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self._page = 1
        self.filter_and_paginate()

    def load_page(self, page):
        if page:
            self._page = int(page)
            self.filter_and_paginate()

    def remove_paper(self, paper_id):
        try:
            user = User.nodes.get(userId=self.request.session.get('user_id'))
            paper = Paper.nodes.get(paperId=paper_id)
            user.saves_papers.disconnect(paper)
            
            self._all_papers = [p for p in self._all_papers if p['paperId'] != paper_id]
            self.total_paper_count = len(self._all_papers)
            self.filter_and_paginate()
        except Exception as e:
            logger.error(f"Async error removing saved paper: {e}", exc_info=True)
            self.error = "Gagal menghapus karya ilmiah."
