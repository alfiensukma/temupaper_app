from django_unicorn.components import UnicornView

class SearchableDropdownView(UnicornView):
    options = []
    filtered_options = []
    selected = ""
    search_query = ""
    name = ""
    label = ""
    placeholder = ""
    is_open = False
    
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
        elif self.name == "major":
            self.options = [
                "Teknik Informatika",
                "Sistem Informasi",
                "Ilmu Komputer",
                "Teknologi Informasi",
                "Data Science"
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
        self.is_open = False
        self.search_query = "" 
        self.filtered_options = self.options
