from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.embedder_wrapper = None

    def ready(self):
        if not self.embedder_wrapper:
            try:
                logger.info("Server starting: Pre-loading and creating Embedder Wrapper...")
                from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
                
                self.embedder_wrapper = SentenceTransformerEmbeddings(model="all-mpnet-base-v2")
                
                logger.info("Embedder Wrapper pre-loaded successfully.")
            except Exception as e:
                logger.error(f"FATAL: Failed to create embedder wrapper on startup: {e}")