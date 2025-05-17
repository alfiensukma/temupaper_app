from django.shortcuts import render, redirect
from app.decorators import login_required, admin_required

@admin_required
def kelola_karya_ilmiah(request):  

    context = {
        'active_menu': 'kelola_karya_ilmiah',
        'papers': range(1, 21)
    }

    return render(request, 'karya-ilmiah/index.html', context)
