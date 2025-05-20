from .paper_importer import PaperImporter
from .author_importer import AuthorImporter
from .journal_importer import JournalImporter
from .institution_importer import InstitutionImporter
from .field_of_study_importer import FieldOfStudyImporter
from .publication_type_importer import PublicationTypeImporter
from .reference_importer import ReferenceImporter
from .topic_importer import TopicImporter

class ImporterFactory:
    @staticmethod
    def create_importer(importer_type, file_path, **kwargs):
        importers = {
            "paper": PaperImporter,
            "author": AuthorImporter,
            "journal": JournalImporter,
            "institution": InstitutionImporter,
            "field_of_study": FieldOfStudyImporter,
            "publication_type": PublicationTypeImporter,
            "reference": ReferenceImporter,
            "topic": TopicImporter,
        }
        importer_class = importers.get(importer_type)
        if not importer_class:
            raise ValueError(f"Unknown importer type: {importer_type}")
        return importer_class(file_path, **kwargs)