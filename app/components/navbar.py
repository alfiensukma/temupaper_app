from django_unicorn.components import UnicornView
from django.urls import reverse

class NavbarView(UnicornView):
    is_dropdown_open = False
    dropdown_items = []
    current_path = ""
    active_paths = []
    search_query = ""

    def mount(self):
        self.current_path = self.request.path.rstrip('/')

        url_query = self.request.GET.get('query', '')
        if url_query:
            self.search_query = url_query

        is_authenticated = self.request.session.get('is_authenticated', False)
        
        if is_authenticated:
            self.dropdown_items = [
                {"name": "Institusi Sejawat", "url": "/peer-institution-recommendation"},
                {"name": "Riwayat Akses", "url": "/access-history-recommendation"},
            ]

        self.active_paths = [item["url"] for item in self.dropdown_items if item["url"] != "#"]

    def toggle_dropdown(self):
        self.is_dropdown_open = not self.is_dropdown_open