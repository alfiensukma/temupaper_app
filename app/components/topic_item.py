from django_unicorn.components import UnicornView
from django.shortcuts import redirect

class TopicItemView(UnicornView):
    topic: str = ""
