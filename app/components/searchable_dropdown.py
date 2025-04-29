from django_unicorn.components import UnicornView

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
            self.options = [
                "Politeknik Negeri Bandung",
                "Universitas Indonesia",
                "Institut Teknologi Bandung",
                "Universitas Gadjah Mada",
                "Institut Teknologi Sepuluh Nopember",
                "Universitas Brawijaya"
            ]

    def updated_search_query(self, value):
        if value:
            self.filtered_options = [
                opt for opt in self.options 
                if value.lower() in opt.lower()
            ]
        else:
            self.filtered_options = self.options

    def select_option(self, value):
        self.selected = value
        self.search_query = "" 
        self.filtered_options = self.options
