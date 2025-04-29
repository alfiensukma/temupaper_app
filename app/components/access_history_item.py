from django_unicorn.components import UnicornView
class AccessHistoryItemView(UnicornView):
    topic = ""
    topic_papers = {}
    paper = []
    
    def mount(self):
        if not hasattr(self, 'topic_papers'):
            self.topic_papers = {}
        if not hasattr(self, 'paper'):
            self.paper = []
        
        if not isinstance(self.topic_papers, dict):
            self.topic_papers = {}
