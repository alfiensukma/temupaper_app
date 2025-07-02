from django.shortcuts import render

def peer_institution(request):
    return render(request, "base.html", {
        "content_template": "peer-institution-recommendation/index.html",
        "body_class": "bg-gray-100",
        "show_search_form": False,
    })