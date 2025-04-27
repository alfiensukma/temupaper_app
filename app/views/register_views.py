from django.shortcuts import render

def register_view(request):
    return render(request, "base.html", {
        "content_template": "auth/register.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })