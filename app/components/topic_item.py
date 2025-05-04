from django_unicorn.components import UnicornView
from django.shortcuts import redirect

class TopicItemView(UnicornView):
    topic = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.topic is None:
            self.topic = {"id": "", "name": ""}
        elif isinstance(self.topic, str):
            # Jika topic adalah string, konversi ke dictionary
            self.topic = {"id": self.topic, "name": self.topic}