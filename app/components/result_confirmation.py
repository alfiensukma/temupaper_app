from django_unicorn.components import UnicornView


class ResultConfirmationView(UnicornView):
    history_papers = []

    def mount(self):
        if hasattr(self, 'history_papers'):
            self.history_papers = self.history_papers
        else:
            self.history_papers = []
