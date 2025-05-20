from django.urls import path, include
from .views.dashboard import admin_dashboard
from .views.kelola_karya_ilmiah import kelola_karya_ilmiah, datatable_paper_json, delete_paper, manage_paper, scraping_view
from .views.upload_views import upload_temp_files, start_import, get_progress

app_name = 'admin_app'

urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path("unicorn/", include("django_unicorn.urls")),
    path('kelola-karya-ilmiah/', kelola_karya_ilmiah, name='kelola_karya_ilmiah'),
    path('datatable-paper-json/', datatable_paper_json, name='datatable_paper_json'),
    path('delete-paper/', delete_paper, name='delete_paper'),
    path('manage-paper/', manage_paper, name='manage_paper'),
    path('upload-temp-files/', upload_temp_files, name='upload_temp_files'),
    path('start-import/', start_import, name='start_import'),
    path('get-progress/', get_progress, name='get_progress'),
    path('scraping/', scraping_view, name='scraping_view'),
]