def theme_processor(request):
    return {
        'is_dark_mode': request.session.get('is_dark_mode', False),
    }