from django_unicorn.components import UnicornView

class TopicHistoryModalView(UnicornView):
    show_modal = False
    selected_topic = ""
    papers = []
    
    def mount(self):
        self.topic_papers = {
            "AI": [
                {"title": "Advances in Artificial Intelligence"},
                {"title": "AI for Healthcare"}
            ],
            "Data Science": [
                {"title": "Data Science for Business"}
            ],
            "Machine Learning": [
                {"title": "Deep Learning Techniques"}
            ]
        }
    
    def show_papers_for_topic(self, topic):
        self.selected_topic = topic
        self.papers = self.topic_papers.get(topic, [])
        self.show_modal = True
        return False
    
    def close_modal(self):
        self.show_modal = False
        return False