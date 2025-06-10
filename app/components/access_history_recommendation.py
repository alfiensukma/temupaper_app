from django_unicorn.components import UnicornView
from django.core.paginator import Paginator
import json

class AccessHistoryRecommendationView(UnicornView):
    all_papers_json = "[]"
    page_obj = None
    _all_papers = []

    def mount(self):
        self._all_papers = json.loads(self.all_papers_json)
        self.paginate(1)

    def paginate(self, page_number):
        if self._all_papers:
            paginator = Paginator(self._all_papers, 10)
            self.page_obj = paginator.get_page(page_number)

    def load_page(self, page_number):
        self.paginate(page_number)