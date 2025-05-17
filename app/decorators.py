# decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('is_authenticated', False):
            messages.error(request, 'Silakan login terlebih dahulu.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('is_authenticated', False):
            messages.error(request, 'Silakan login terlebih dahulu.')
            return redirect('login')
        
        if not request.session.get('is_admin', False):
            messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
            return redirect('index')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def user_only(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('is_authenticated', False):
            messages.error(request, 'Silakan login terlebih dahulu.')
            return redirect('login')
        
        if request.session.get('is_admin', False):
            messages.info(request, 'Anda telah login sebagai admin. Diarahkan ke dashboard admin.')
            return redirect('login')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

