from django.urls import path, include
from .views.retrieve_paper_views import fetch_papers
from .views.graph_views import generate_knowledge_graph, import_topic, import_institution, import_journal
from .views.detail_views import get_recommendation, get_detail_paper, record_paper_read
from .views.search_views import index, search
from .views.topic_recommendation_views import topic_list, topic_result
from .views.peer_institution_recommendation_views import peer_institution
from .views.similarity_access_recommendation_views import similarity_access
from .views.access_history_recommendation_views import access_history
from .views.login_views import login_view
from .views.register_views import register_view
from .views.verification_code_views import verification_code, resend_verification_code
from .views.verification_email_views import verification_email, verification_codes
from .views.profile_views import reset_password, profile_view, edit_profile
from .views.logout_view import logout_view
from .views.save_paper import save_paper_list
from .views.embedding_views import EmbeddingView
from .views.preprocessing_views import create_similar_paper_relation, create_page_rank

urlpatterns = [
    path('', index, name='index'),
    path("unicorn/", include("django_unicorn.urls")),
    path("fetch-papers/", fetch_papers, name="get_paper"),
    path("paper/detail/", get_detail_paper, name="get_detail"),
    path("paper/detail/recommendation", get_recommendation, name="get_recommendation"),
    path("generate-knowledge-graph/", generate_knowledge_graph, name="generate_knowledge_graph"),
    path('import-topic/', import_topic, name='import_topic'),
    path('import-institution/', import_institution, name='import_institution'),
    path('import-journal/', import_journal, name='import_journal'),

    path('search/', search, name='search'),
    path('papers/detail/<str:paper_id>/', get_detail_paper, name='paper_detail'),
    path('topic-recommendation/', topic_list, name='topic_list'),
    path("topic-recommendation/<str:topic>", topic_result, name="topic_result"),
    path('peer-institution-recommendation/', peer_institution, name='peer_institution'),
    path('similarity-access-recommendation/', similarity_access, name='similarity_access'),
    path('access-history-recommendation/', access_history, name='access_history'),
    path('login/', login_view, name='login_view'),
    path('register/', register_view, name='register_view'),
    path('verification-code/', verification_code, name='verification_code'),
    path('verification-code-forgot-password/', verification_codes, name='verification_codes'),
    path('verification-email/', verification_email, name='verification_email'),
    path('reset-password/', reset_password, name='reset_password'),
    path('profile/', profile_view, name='profile_view'),
    path('logout/', logout_view, name='logout'),
    path('edit-profile/', edit_profile, name='edit_profile'),
    path('save-paper-list/', save_paper_list, name='save_paper_list'),
    path('resend-verification-code/', resend_verification_code, name='resend_verification_code'),
    path('record-paper-read/', record_paper_read, name='record_paper_read'),
    path('create-search-embedding/', EmbeddingView.as_view(), name='create_search_embedding'),
    path('create-similar-paper-relation/', create_similar_paper_relation, name='create_similar_paper_relation'),
    path('create-page-rank/', create_page_rank, name='create_page_rank'),

]