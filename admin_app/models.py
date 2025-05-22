from datetime import datetime
import uuid
class HistoryRecord:
    def __init__(self, operation_type, details=None, status="success"):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.operation_type = operation_type
        self.details = details or {}
        self.status = status
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "operation_type": self.operation_type,
            "details": self.details,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data):
        record = cls(
            operation_type=data.get("operation_type", "unknown"),
            details=data.get("details", {}),
            status=data.get("status", "unknown")
        )
        record.id = data.get("id", str(uuid.uuid4()))
        record.timestamp = data.get("timestamp", datetime.now().isoformat())
        return record