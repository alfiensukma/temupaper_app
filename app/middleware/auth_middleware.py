# app/middleware/auth_middleware.py
from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of protected route names that require authentication
        protected_routes = [
            'peer_institution',
            'similarity_access',
            'access_history'
        ]
        
        try:
            # Try to resolve the current URL to a view name
            current_route_name = resolve(request.path_info).url_name
            
            # Check if the current route requires authentication
            requires_auth = current_route_name in protected_routes
            
            # Check if user is authenticated
            is_authenticated = request.session.get('is_authenticated', False)
            
            # If route requires auth and user is not authenticated, redirect to login
            if requires_auth and not is_authenticated:
                return redirect('login_view')
                
        except Resolver404:
            # If URL cannot be resolved, just continue
            pass
            
        response = self.get_response(request)
        return response