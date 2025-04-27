from django_unicorn.components import UnicornView

class PaperCarouselView(UnicornView):
    papers = []
    current_slide = 0
    
    def mount(self):
        if not self.papers:
            self.papers = []
    
    def next_slide(self):
        if len(self.papers) > 0:
            self.current_slide = (self.current_slide + 1) % len(self.papers)
    
    def prev_slide(self):
        if len(self.papers) > 0:
            self.current_slide = (self.current_slide - 1) % len(self.papers)
    
    def go_to_slide(self, slide):
        if 0 <= slide < len(self.papers):
            self.current_slide = slide