from app.utils.neo4j_connection import Neo4jConnection
from admin_app.models import HistoryRecord
import logging

logger = logging.getLogger(__name__)

class HistoryService:
    def __init__(self):
        self.neo4j_conn = Neo4jConnection()
    
    def add_history(self, operation_type, details=None, status="success"):
        try:
            record = HistoryRecord(
                operation_type=operation_type,
                details=details,
                status=status
            )
            
            query = """
            CREATE (h:History {
                id: $id,
                timestamp: $timestamp, 
                operation_type: $operation_type,
                details: $details,
                status: $status
            })
            RETURN h
            """
            
            params = record.to_dict()
            params["details"] = str(params["details"])
            
            with self.neo4j_conn.get_driver().session() as session:
                result = session.run(query, params)
                node = result.single()
                logger.info(f"Added history record: {record.id}")
                return record.to_dict()
        except Exception as e:
            logger.error(f"Failed to add history record: {str(e)}")
            return None
        finally:
            self.neo4j_conn.close()
    
    def update_history(self, history_id, details=None, status=None):
        try:
            query = "MATCH (h:History {id: $id}) "
            params = {"id": history_id}
            
            if details is not None and status is not None:
                query += "SET h.details = $details, h.status = $status "
                params["details"] = str(details)
                params["status"] = status
            elif details is not None:
                query += "SET h.details = $details "
                params["details"] = str(details)
            elif status is not None:
                query += "SET h.status = $status "
                params["status"] = status
                
            query += "RETURN h"
            
            with self.neo4j_conn.get_driver().session() as session:
                result = session.run(query, params)
                node = result.single()
                return node["h"] if node else None
        except Exception as e:
            logger.error(f"Failed to update history record: {str(e)}")
            return None
        finally:
            self.neo4j_conn.close()
    
    def get_history(self, limit=100, operation_type=None):
        try:
            query = "MATCH (h:History) "
            params = {}
            
            if operation_type:
                query += "WHERE h.operation_type = $operation_type "
                params["operation_type"] = operation_type
            
            query += "RETURN h ORDER BY h.timestamp DESC LIMIT $limit"
            params["limit"] = limit
            
            history_records = []
            with self.neo4j_conn.get_driver().session() as session:
                result = session.run(query, params)
                for record in result:
                    node = record.get("h")
                    if node:
                        data = dict(node)
                        try:
                            import ast
                            data["details"] = ast.literal_eval(data["details"])
                        except:
                            data["details"] = {}
                        history_records.append(data)
            
            return history_records
        except Exception as e:
            logger.error(f"Failed to get history records: {str(e)}")
            return []
        finally:
            self.neo4j_conn.close()