from django_unicorn.components import UnicornView

class PaperItemView(UnicornView):
    title: str = ""
    authors: list = []
    date: str = ""
    abstract: str = ""
