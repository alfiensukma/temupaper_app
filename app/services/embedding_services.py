import numpy as np
import logging
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
from app.models import Paper

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_name="all-mpnet-base-v2"):
        self.embedder = SentenceTransformerEmbeddings(model=model_name)

    def get_paper_without_embedding(self):
        """
        Mengambil semua paper yang belum memiliki search_embedding.
        """
        papers = Paper.nodes.filter(search_embedding__isnull=True).all()
        return [{'paperId': paper.paperId, 'title': paper.title, 'abstract': paper.abstract} for paper in papers]

    def create_embeddings(self, papers_data):
        """
        Membuat embedding untuk setiap paper berdasarkan judul dan abstrak.
        """
        combined_texts = [
            f"Title: {paper['title']} Abstract: {paper['abstract']}" 
            for paper in papers_data
        ]
        return [self.embedder.embed_query(text) for text in combined_texts]

    def save_embeddings(self, papers_data, embeddings_list):
        """
        Menyimpan embedding ke dalam database.
        """
        success_count = 0
        error_count = 0

        for paper_data, embedding in zip(papers_data, embeddings_list):
            paper_id = paper_data['paperId']
            try:
                paper = Paper.nodes.get(paperId=paper_id)
                if isinstance(embedding, np.ndarray):
                    paper.search_embedding = embedding.tolist()
                else:
                    paper.search_embedding = embedding
                paper.save()
                success_count += 1
            except Exception as e:
                logger.error(f"Error saving embedding for paper {paper_id}: {str(e)}")
                error_count += 1

        return success_count, error_count