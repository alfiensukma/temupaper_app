from django.shortcuts import render

def access_history(request):
    return render(request, "base.html", {
        "content_template": "access-history-recommendation/index.html",
        "body_class": "bg-gray-100",
        "show_search_form": False,
    })