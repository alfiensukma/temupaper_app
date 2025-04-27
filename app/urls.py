from django.urls import path, include
from .views.retrieve_paper_views import fetch_papers, fetch_papers_by_reference_ids
from .views.graph_views import generate_knowledge_graph
from .views.detail_views import get_recommendation, get_detail_json, get_paper_detail
from .views.search_views import index, search
from .views.topic_recommendation_views import topic_list, topic_result
from .views.peer_institution_recommendation import peer_institution
from .views.similarity_access_recommendation import similarity_access
from .views.access_history_recommendation import access_history
from .views.login_views import login_view
from .views.register_views import register_view
from .views.verification_code_views import verification_code
from .views.verification_email_views import verification_email
from .views.profile_views import reset_password, profile_view, edit_profile

urlpatterns = [
    path('', index, name='index'),
    path("unicorn/", include("django_unicorn.urls")),
    path("fetch-papers/", fetch_papers, name="get_paper"), # support params query, min_year, fields_of_study, limit, reference_limit
    path("fetch-references/", fetch_papers_by_reference_ids, name="fetch_papers_by_reference_ids"),
    path("paper/detail/", get_detail_json, name="get_detail"),
    path("paper/detail/recommendation", get_recommendation, name="get_recommendation"),
    path("generate-knowledge-graph/", generate_knowledge_graph, name="generate_knowledge_graph"),

    path('search/', search, name='search'),
    path('papers/detail/<str:paper_id>/', get_paper_detail, name='paper_detail'),
    path('topic-recommendation/', topic_list, name='topic_list'),
    path("topic-recommendation/<str:topic>", topic_result, name="topic_result"),
    path('peer-institution-recommendation/', peer_institution, name='peer_institution'),
    path('similarity-access-recommendation/', similarity_access, name='similarity_access'),
    path('access-history-recommendation/', access_history, name='access_history'),
    path('login/', login_view, name='login_view'),
    path('register/', register_view, name='register_view'),
    path('verification-code/', verification_code, name='verification_code'),
    path('verification-email/', verification_email, name='verification_email'),
    path('reset-password/', reset_password, name='reset_password'),
    path('profile/', profile_view, name='profile_view'),
]