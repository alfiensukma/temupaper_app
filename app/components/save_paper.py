from django_unicorn.components import UnicornView


class SavePaperView(UnicornView):
    is_saved = False
    show_notification = False
    
    def save_paper(self):
        self.is_saved = True
        self.show_notification = True
