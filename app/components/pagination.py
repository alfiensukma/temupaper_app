from django_unicorn.components import UnicornView


class PaginationView(UnicornView):
    paginator: dict = None
