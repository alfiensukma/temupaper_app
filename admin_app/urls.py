from django.urls import path, include
from .views.dashboard import admin_dashboard
from .views.kelola_karya_ilmiah import kelola_karya_ilmiah

app_name = 'admin'

urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('kelola-karya-ilmiah/', kelola_karya_ilmiah, name='kelola_karya_ilmiah'),
]