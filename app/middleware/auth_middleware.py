from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from django.contrib import messages

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        protected_routes = [
            'peer_institution',
            'similarity_access',
            'access_history',
            'profile_view',
            'save_paper_list',
            'edit_profile',
        ]
        
        admin_routes = [
            'admin_dashboard',
            'manage_papers',
        ]
        

        public_routes_for_guests_only = ['login_view', 'register_view']
        
        is_authenticated = request.session.get('is_authenticated', False)
        is_admin = request.session.get('is_admin', False)

        try:
            current_route_name = resolve(request.path_info).url_name
            if is_authenticated and current_route_name in public_routes_for_guests_only:
                return redirect('/')

            if current_route_name in protected_routes and not is_authenticated:
                messages.error(request, 'Silakan login terlebih dahulu untuk mengakses halaman ini.')
                return redirect('login_view')

            if current_route_name in admin_routes and not is_admin:
                if is_authenticated:
                    messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
                    return redirect('/')
                else:
                    messages.error(request, 'Silakan login terlebih dahulu untuk mengakses halaman ini.')
                    return redirect('login_view')

        except Resolver404:
            pass

        response = self.get_response(request)
        return response