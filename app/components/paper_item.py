import logging
from django_unicorn.components import UnicornView

logger = logging.getLogger(__name__)

class PaperItemView(UnicornView):
    paper_id: str = ""
    title: str = ""
    authors: list = []
    date: str = ""
    abstract: str = ""

    def mount(self):
        pass