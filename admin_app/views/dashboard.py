from django.shortcuts import render, redirect
from app.decorators import login_required, admin_required

@admin_required
def admin_dashboard(request):  

    context = {
        'active_menu': 'dashboard'
    }

    return render(request, 'dashboard/index.html', context)
