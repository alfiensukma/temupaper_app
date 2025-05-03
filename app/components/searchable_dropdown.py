# components/searchable_dropdown.py
from django_unicorn.components import UnicornView
from app.models import Institution

class SearchableDropdownView(UnicornView):
    options = []
    filtered_options = []
    selected = ""
    search_query = ""
    name = ""
    label = ""
    placeholder = ""
    
    def mount(self):
        self.load_options()
        self.filtered_options = self.options
    
    def load_options(self):
        if self.name == "institution":
            institutions = Institution.nodes.all()
            self.options = [institution.name for institution in institutions]
    
    def filter_options(self):
        if self.search_query:
            self.filtered_options = [
                opt for opt in self.options 
                if self.search_query.lower() in opt.lower()
            ]
        else:
            self.filtered_options = self.options
    
    def updated_search_query(self, value):
        self.search_query = value
        self.filter_options()
    
    def select_option(self, value):
        self.selected = value
        self.search_query = ""
        self.filtered_options = self.options