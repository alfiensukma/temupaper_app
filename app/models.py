# app/models.py
from neomodel import (
    StringProperty, 
    StructuredNode, 
    UniqueIdProperty, 
    BooleanProperty,
    RelationshipTo
)
import uuid
from django.contrib.auth.hashers import make_password, check_password

class User(StructuredNode):
    # Remove the default parameter
    userId = UniqueIdProperty()
    name = StringProperty(required=True)
    email = StringProperty(unique_index=True, required=True)
    password = StringProperty(required=True)
    email_verification = StringProperty()
    is_verified = BooleanProperty(default=False)
    
    # Relationship
    affiliated_with = RelationshipTo('Institution', 'AFFILIATED_WITH')
    
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
class Institution(StructuredNode):
    institutionId = StringProperty(unique_index=True)
    name = StringProperty(index=True)
