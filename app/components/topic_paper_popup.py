from django_unicorn.components import UnicornView


class TopicPaperPopupView(UnicornView):
    topic = ""
    topic_papers = []

    def mount(self):
        pass
