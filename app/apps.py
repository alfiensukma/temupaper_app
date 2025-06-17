from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.embedder_model = None

    def ready(self):
        if not self.embedder_model:
            try:
                logger.info("Server starting: Pre-loading SentenceTransformer model into memory...")
                from sentence_transformers import SentenceTransformer
                self.embedder_model = SentenceTransformer("all-mpnet-base-v2")
                logger.info("Embedding model pre-loaded successfully.")
            except Exception as e:
                logger.error(f"FATAL: Failed to load embedding model on startup: {e}")