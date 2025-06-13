from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    _embedder = None

    @property
    def embedder(self):
        if self._embedder is None:
            try:
                from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
                logger.info("Initializing SentenceTransformer model...")
                self._embedder = SentenceTransformerEmbeddings(model="all-mpnet-base-v2")
                logger.info("SentenceTransformer model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to initialize embedder: {str(e)}")
                raise
        return self._embedder

    def ready(self):
        try:
            _ = self.embedder
            logger.info("App ready: Embedder initialized successfully")
        except Exception as e:
            logger.error(f"App ready failed: {str(e)}")
            raise
