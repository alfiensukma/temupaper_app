from django.urls import path
from .views.retrieve_paper_views import fetch_papers
from .views.retrieve_paper_views import fetch_papers_by_reference_ids
from .views.graph_views import generate_knowledge_graph
from .views.recommendation_views import get_all_paper_titles

urlpatterns = [
    path("fetch-papers/", fetch_papers, name="get_paper"), # support params query, min_year, fields_of_study, limit, reference_limit
    path("fetch-references/", fetch_papers_by_reference_ids, name="fetch_papers_by_reference_ids"),
    path("paper/recommendations/by-id/", get_all_paper_titles, name="get_all_paper_titles"),
    path("generate-knowledge-graph/", generate_knowledge_graph, name="generate_knowledge_graph"),
]