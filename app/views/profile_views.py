from django.shortcuts import render

def reset_password(request):
    return render(request, "base.html", {
        "content_template": "auth/reset-password.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })
    
def profile_view(request):
    return render(request, "base.html", {
        "content_template": "auth/profile.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })

def edit_profile(request):
    pass