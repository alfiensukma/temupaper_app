from django_unicorn.components import UnicornView

class RecommendationModifierModalView(UnicornView):
    show = False
    show_error = False
    selected_papers = []
    history_papers = []
    MAX_SELECTIONS = 5

    def mount(self):
        if hasattr(self, 'history_papers'):
            self.history_papers = self.history_papers
            self.selected_papers = []
            self.show_error = False

    def handle_paper_selection(self, paper_id):
        if paper_id in self.selected_papers:
            self.selected_papers.remove(paper_id)
            self.show_error = False
            return

        if len(self.selected_papers) >= self.MAX_SELECTIONS:
            self.show_error = True
            return False
        
        self.selected_papers.append(paper_id)
        self.show_error = False
        return True
    
    def apply_changes(self):
        self.show_error = False
