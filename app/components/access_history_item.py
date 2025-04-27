from django_unicorn.components import UnicornView

class AccessHistoryItemView(UnicornView):
    topic = ""
    modal_id = ""
    
    def show_topic_papers(self):
        return {
            "javascript": f"""
                Unicorn.getComponentById('{self.modal_id}').call('show_papers_for_topic', '{self.topic}');
                return false;
            """
        }
