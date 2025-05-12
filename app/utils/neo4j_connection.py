from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

class Neo4jConnection:
    def __init__(self):
        load_dotenv()
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = None
        self._connect()

    def _connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        except Exception as e:
            raise Exception(f"Failed to connect to Neo4j: {str(e)}")

    def get_driver(self):
        return self.driver

    def close(self):
        if self.driver:
            self.driver.close()
            self.driver = None