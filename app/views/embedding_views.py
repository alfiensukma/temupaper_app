import pandas as pd
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
from app.models import Paper
import logging
import numpy as np
from django.http import JsonResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
embedder = SentenceTransformerEmbeddings(model="all-mpnet-base-v2")

def get_paper_without_embedding():
    # Menggunakan filter untuk mendapatkan Paper tanpa search_embedding
    # Catatan: has_property=False berarti properti tersebut tidak ada di node
    papers = Paper.nodes.filter(search_embedding__isnull=True).all()
    
    result = [{'paperId': paper.paperId, 'title': paper.title, 'abstract': paper.abstract} 
              for paper in papers]
    return result

def create_and_save_search_embedding(request):
    try:
        # Langkah 1: Ambil data paper
        papers_data = get_paper_without_embedding()
        
        if not papers_data:
            logger.info("No papers found without search_embedding")
            return JsonResponse({"message": "No papers found without search embedding"}, status=200)
        
        # Langkah 2: Buat embedding dari data
        combined_texts = [
            f"Title: {paper['title']} Abstract: {paper['abstract']}" 
            for paper in papers_data
        ]
        
        embeddings_list = [embedder.embed_query(text) for text in combined_texts]
        
        # Langkah 3: Simpan embedding ke node yang sesuai
        success_count = 0
        error_count = 0
        
        for paper_data, embedding in zip(papers_data, embeddings_list):
            paper_id = paper_data['paperId']
            try:
                # Cari paper berdasarkan ID
                paper = Paper.nodes.get(paperId=paper_id)
                
                # Periksa tipe data embedding dan simpan dengan format yang benar
                if isinstance(embedding, np.ndarray):
                    # Jika numpy array, konversi ke list
                    paper.search_embedding = embedding.tolist()
                else:
                    # Jika sudah list, gunakan langsung
                    paper.search_embedding = embedding
                    
                paper.save()  # Simpan perubahan ke database
                success_count += 1
            except Exception as e:
                logger.error(f"Error saving embedding for paper {paper_id}: {str(e)}")
                error_count += 1
        
        message = f"Updated search embeddings for {success_count} papers. Errors: {error_count}"
        logger.info(message)
        
        # Tambahkan return statement di sini
        return JsonResponse({
            "message": message,
            "success_count": success_count,
            "error_count": error_count
        }, status=200)
        
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message)
        # Juga tambahkan return di sini untuk kasus error
        return JsonResponse({"error": error_message}, status=500)
            