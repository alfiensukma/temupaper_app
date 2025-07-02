import logging
from django_unicorn.components import UnicornView
from django.core.paginator import Paginator
from app.utils.neo4j_connection import Neo4jConnection
from app.utils.parse_indonesian_date import format_date_to_indonesian

logger = logging.getLogger(__name__)

class CitationListView(UnicornView):
    paper_id = ""
    search_query = ""
    papers = []
    pagination_data = None
    _all_papers = []
    _page = 1
    results_count = 0
    
    def mount(self):
        self.load_citations()
        self.filter_and_paginate()

    def load_citations(self):
        driver = None
        try:
            neo4j_connection = Neo4jConnection()
            driver = neo4j_connection.get_driver()
            with driver.session() as session:
                result = session.run("""
                    MATCH (p:Paper {paperId: $paperId})<-[:REFERENCES]-(citation:Paper)
                    OPTIONAL MATCH (citation)-[:AUTHORED_BY]->(author:Author)
                    RETURN 
                    citation.paperId AS paperId,
                    citation.title AS title,
                    collect(author.name) AS authors,
                    citation.year AS year,
                    citation.publicationDate AS date,
                    citation.abstract as abstract
                """, paperId=self.paper_id)
                
                papers_raw = list(result)
            
                processed_papers = []
                for record in papers_raw:
                    paper = dict(record)
                    
                    paper["date"] = format_date_to_indonesian(
                        paper.get("date"), 
                        fallback_year=paper.get("year", "N/A")
                    )
                    processed_papers.append(paper)
                
                self._all_papers = processed_papers
        finally:
            if driver:
                driver.close()

    def filter_and_paginate(self):
        filtered_list = self._all_papers
        if self.search_query:
            query = self.search_query.lower()
            filtered_list = [p for p in filtered_list if query in p['title'].lower()]
        
        self.results_count = len(filtered_list)
        paginator = Paginator(filtered_list, 3)
        self._page = min(max(1, self._page), paginator.num_pages)
        page_obj = paginator.get_page(self._page)
        self.papers = list(page_obj.object_list)
        self.pagination_data = { 
            'number': self._page, 
            'num_pages': paginator.num_pages, 
            'has_previous': page_obj.has_previous(), 
            'has_next': page_obj.has_next(), 
            'previous_page_number': page_obj.previous_page_number() 
                if page_obj.has_previous() else None, 
            'next_page_number': page_obj.next_page_number() 
                if page_obj.has_next() else None
        }

    def updated_search_query(self, value):
        self._page = 1
        self.filter_and_paginate()

    def load_page(self, page_number):
        self._page = int(page_number)
        self.filter_and_paginate()