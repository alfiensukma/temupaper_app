from neomodel import db as neomodel_db
import os
    
class Neo4jConnection:
    def __init__(self):
        self.driver = neomodel_db.driver

    def get_driver(self):
        return self.driver

    def close(self):
        pass