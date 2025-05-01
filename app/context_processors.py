def theme_processor(request):
    return {
        'is_dark_mode': request.session.get('is_dark_mode', False),
    }

# app/context_processors.py

def user_context(request):
    """Make session user data available to templates."""
    is_authenticated = request.session.get('is_authenticated', False)
    
    if is_authenticated:
        user = {
            'is_authenticated': True,
            'first_name': request.session.get('user_name', '').split()[0] if ' ' in request.session.get('user_name', '') else request.session.get('user_name', ''),
            'name': request.session.get('user_name', ''),
            'email': request.session.get('user_email', '')
        }
    else:
        user = {'is_authenticated': False}
    
    return {'user': user}