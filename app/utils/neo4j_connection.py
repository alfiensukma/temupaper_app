from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
import os
import logging

logger = logging.getLogger(__name__)

class Neo4jConnection:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")

        if not password:
            raise ValueError("Password Neo4j (NEO4J_PASSWORD) tidak ditemukan di file .env")

        self.driver = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logger.info("Koneksi Neo4j berhasil dibuat dan diverifikasi.")

        except (ServiceUnavailable, AuthError, ValueError) as e:
            logger.error(f"Gagal membuat koneksi Neo4j: {e}")
            raise
        except Exception as e:
            logger.error(f"Error tak terduga saat koneksi Neo4j: {e}")
            raise

    def get_driver(self):
        return self.driver

    def close(self):
        if self.driver:
            self.driver.close()