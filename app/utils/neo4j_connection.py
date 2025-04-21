from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

def get_neo4j_driver():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', '')
    return GraphDatabase.driver(uri, auth=(username, password))