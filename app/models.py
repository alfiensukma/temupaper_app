from neomodel import (
    StringProperty, 
    StructuredNode, 
    UniqueIdProperty, 
    BooleanProperty,
    RelationshipTo,
    RelationshipFrom,
    IntegerProperty,
    ArrayProperty,
    DateTimeProperty,
    StructuredRel
)
import datetime
import uuid
from django.contrib.auth.hashers import make_password, check_password

# Define the relationship model with timestamp
class SavesPaperRel(StructuredRel):
    saved_at = DateTimeProperty(default=lambda: datetime.datetime.now())

class HasReadRel(StructuredRel):
    read_at = DateTimeProperty(default=lambda: datetime.datetime.now())
    access_method = StringProperty(choices={'doi': 'DOI Link', 'semantic': 'Semantic Scholar'})

class PaperSimilarityRel(StructuredRel):
    score = IntegerProperty()

class PaperHighestSimilarityRel(StructuredRel):
    score = IntegerProperty()


class Role(StructuredNode):
    role_id = StringProperty(unique_index=True)
    nama = StringProperty(required=True)

class User(StructuredNode):
    userId = UniqueIdProperty()
    name = StringProperty(required=True)
    email = StringProperty(unique_index=True, required=True)
    password = StringProperty(required=True)
    email_verification = StringProperty()
    is_verified = BooleanProperty(default=False)
    
    # Relationships
    affiliated_with = RelationshipTo('Institution', 'AFFILIATED_WITH')
    saves_papers = RelationshipTo('Paper', 'SAVES_PAPER', model=SavesPaperRel)
    has_read = RelationshipTo('Paper', 'HAS_READ', model=HasReadRel)
    has_role = RelationshipTo('Role', 'HAS_ROLE')  # Tambahan relasi ke Role
    
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    def get_roles(self):
        """Mendapatkan semua role yang dimiliki user"""
        return [role.nama for role in self.has_role.all()]
    
    def is_admin(self):
        """Memeriksa apakah user memiliki role admin"""
        return 'Admin' in self.get_roles()

class Institution(StructuredNode):
    institutionId = StringProperty(unique_index=True)
    names = StringProperty(index=True)

class Author(StructuredNode):
    authorId = StringProperty(unique_index=True)
    name = StringProperty(index=True)
    
    papers = RelationshipFrom('Paper', 'AUTHORED_BY')

class Paper(StructuredNode):
    paperId = StringProperty(unique_index=True)
    title = StringProperty(index=True)
    abstract = StringProperty()
    citationCount = IntegerProperty(default=0)
    corpusId = StringProperty()
    doi = StringProperty()
    embedding = ArrayProperty()
    search_embedding = ArrayProperty()
    influentialCitationCount = IntegerProperty(default=0)
    publicationDate = StringProperty()
    referenceCount = IntegerProperty(default=0)
    url = StringProperty()
    venue = StringProperty()
    year = IntegerProperty()
    
    saved_by = RelationshipFrom('User', 'SAVES_PAPER', model=SavesPaperRel)
    authored_by = RelationshipTo('Author', 'AUTHORED_BY')
    read_by = RelationshipFrom('User', 'HAS_READ', model=HasReadRel)
    similar = RelationshipTo('Paper', 'SIMILAR', model=PaperSimilarityRel)
    highest_similar = RelationshipTo('Paper', 'HIGHEST_SIMILAR', model=PaperHighestSimilarityRel)
    references = RelationshipTo('Paper', 'REFERENCES')