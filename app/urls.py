from django.urls import path
from .views.retrieve_paper_views import fetch_papers
from .views.retrieve_paper_views import fetch_papers_by_reference_ids
from .views.graph_views import generate_knowledge_graph
from .views.detail_views import get_recommendation
from .views.detail_views import get_detail

urlpatterns = [
    path("fetch-papers/", fetch_papers, name="get_paper"), # support params query, min_year, fields_of_study, limit, reference_limit
    path("fetch-references/", fetch_papers_by_reference_ids, name="fetch_papers_by_reference_ids"),
    path("paper/detail/", get_detail, name="get_detail"),
    path("paper/detail/recommendation", get_recommendation, name="get_recommendation"),
    path("generate-knowledge-graph/", generate_knowledge_graph, name="generate_knowledge_graph"),
]