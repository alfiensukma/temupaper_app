# app/views/logout_view.py
from django.shortcuts import redirect
from django.contrib import messages

def logout_view(request):
    """
    Log out the user by clearing session data and redirect to home.
    """
    # Clear authentication-related session data
    if 'user_id' in request.session:
        del request.session['user_id']
    if 'user_email' in request.session:
        del request.session['user_email']
    if 'user_name' in request.session:
        del request.session['user_name']
    if 'is_authenticated' in request.session:
        del request.session['is_authenticated']
    
    # Optional: clear entire session
    # request.session.flush()
    
    # Add a success message
    messages.success(request, 'Anda telah berhasil keluar.')
    
    # Redirect to homepage
    return redirect('index')