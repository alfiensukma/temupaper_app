from django_unicorn.components import UnicornView
from app.utils.neo4j_connection import Neo4jConnection

class ScrapingTopicView(UnicornView):
    topics = []

    def mount(self):
        conn = Neo4jConnection()
        with conn.get_driver().session() as session:
            result = session.run("MATCH (t:Topic) RETURN t.topicId AS id, t.name AS name, COALESCE(t.paperCount, 0) AS paperCount ORDER BY t.name")
            self.topics = [
                {
                    "id": row["id"], 
                    "name": row["name"],
                    "paperCount": row["paperCount"] 
                } for row in result
            ]
