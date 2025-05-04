import os
import csv
import spacy
import logging
import json
import ast
from rdflib import Graph, Namespace
from app.utils.neo4j_connection import get_neo4j_driver
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
nlp = spacy.load("en_core_web_lg")  # Load spaCy model

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CSV_DIR = os.path.join(BASE_DIR, "data-csv")
DATA_RDF_DIR = os.path.join(BASE_DIR, "data-rdf")
PAPERS_PATH = os.path.join(DATA_CSV_DIR, "papers-dummy.csv")
PAPER_REFERENCES_PATH = os.path.join(DATA_CSV_DIR, "paper-references.csv")
REFERENCES_PATH = os.path.join(DATA_CSV_DIR, "references.csv")
CSO_RDF_PATH = os.path.join(DATA_RDF_DIR, "cso.ttl")

def parse_cso_rdf(rdf_file_path):
    if not os.path.exists(rdf_file_path):
        logger.error(f"File {rdf_file_path} not found")
        return [], []

    g = Graph()
    try:
        g.parse(rdf_file_path, format="turtle")
    except Exception as e:
        logger.error(f"Error while parsing RDF file: {e}")
        return [], []

    CSO = Namespace("http://cso.kmi.open.ac.uk/schema/cso#")
    RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
    
    logger.info("Parsing CSO namespaces")
    
    hierarchy = []
    topic_labels = {}
    unique_topics = set()

    try:
        # Extract topics and labels
        for s, p, o in g.triples((None, RDFS.label, None)):
            topic_uri = str(s)
            label = str(o) if o else ""
            
            if label:
                label = label.lower().replace(' ', '_')
                topic_labels[topic_uri] = label

        # First, collect direct children of computer_science
        level_1_topics = set()
        for s, p, o in g.triples((None, CSO.superTopicOf, None)):
            parent = topic_labels.get(str(s), "").lower()
            child = topic_labels.get(str(o), "").lower()
            
            if parent == "computer_science":
                level_1_topics.add(child)
                unique_topics.add(child)

        # Then collect children of level 1 topics (level 2)
        for s, p, o in g.triples((None, CSO.superTopicOf, None)):
            parent = topic_labels.get(str(s), "").lower()
            child = topic_labels.get(str(o), "").lower()
            
            if parent in level_1_topics:
                hierarchy.append((child, parent))
                unique_topics.add(child)
                unique_topics.add(parent)

        # Create topics with numeric IDs (excluding computer_science)
        topics = []
        for idx, name in enumerate(sorted(unique_topics)):
            if name != "computer_science":
                topics.append({"id": idx + 1, "name": name})
        
        logger.info(f"Filtered hierarchy: {len(hierarchy)}, Topics: {len(topics)}")
        return topics, hierarchy

    except Exception as e:
        logger.error(f"Error processing RDF data: {e}")
        return [], []

def extract_topics(title, abstract, cso_topics):
    text = (title or "") + " " + (abstract or "")
    if not text.strip():
        logger.warning("Empty text for topic extraction")
        return []
    
    doc = nlp(text.lower())
    topics = set()
    
    for topic in cso_topics:
        topic_with_space = topic.replace('_', ' ')
        # Pencocokan eksak
        if topic_with_space in doc.text:
            topics.add(topic)
        # Pencocokan berbasis token
        else:
            topic_doc = nlp(topic_with_space)
            for chunk in doc.noun_chunks:
                if chunk.text == topic_with_space:
                    topics.add(topic)
                    break
                if chunk.has_vector and topic_doc.has_vector:
                    similarity = chunk.similarity(topic_doc)
                    if similarity > 0.9:  # Threshold
                        topics.add(topic)
                        break
    
    return list(topics)

def import_cso_hierarchy(driver, topics, hierarchy):
    query_topics = """
    UNWIND $topics AS topic
    MERGE (t:Topic {name: topic.name})
    SET t.id = toInteger(topic.id)
    """
    with driver.session() as session:
        session.run(query_topics, topics=topics)
    
    query_hierarchy = """
    UNWIND $hierarchy AS pair
    MATCH (child:Topic {name: pair[0]})
    MATCH (parent:Topic {name: pair[1]})
    MERGE (child)-[:SUB_TOPIC_OF]->(parent)
    """
    with driver.session() as session:
        session.run(query_hierarchy, hierarchy=[[child, parent] for child, parent in hierarchy])

def count_csv_rows(file_path):
    if not os.path.exists(file_path):
        return 0
    with open(file_path, mode='r', encoding='utf-8') as f:
        return sum(1 for row in csv.DictReader(f))

def clear_neo4j(driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

# paper nodes
def import_papers_nodes(driver, file_path, is_reference=False):
    papers = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            external_ids_str = row.get("externalIds", "{}")
            try:
                external_ids = ast.literal_eval(external_ids_str)
                doi = external_ids.get("DOI", "")
            except Exception:
                doi = ""
           
            papers.append({
                "paperId": row["paperId"],
                "corpusId": row.get("corpusId", ""),
                "doi": doi,
                "title": row.get("title", ""),
                "year": row.get("year", ""),
                "abstract": row.get("abstract", ""),
                "url": row.get("url", ""),
                "publicationDate": row.get("publicationDate", ""),
                "venue": row.get("venue", ""),
                "citationCount": row.get("citationCount", ""),
                "influentialCitationCount": row.get("influentialCitationCount", ""),
                "embedding": row.get("embedding", ""),
                "referenceCount": row.get("referenceCount", ""),
            })
    
    query = """
    UNWIND $papers AS row
    MERGE (p:Paper {paperId: row.paperId})
    SET p.corpusId = row.corpusId,
        p.doi = row.doi,
        p.title = row.title,
        p.year = toInteger(row.year),
        p.abstract = row.abstract,
        p.url = row.url,
        p.publicationDate = row.publicationDate,
        p.venue = row.venue,
        p.citationCount = toInteger(row.citationCount),
        p.influentialCitationCount = toInteger(row.citationCount),
        p.embedding = apoc.convert.fromJsonList(row.embedding),
        p.referenceCount = toInteger(row.referenceCount)
    """
    
    with driver.session() as session:
        session.run(query, papers=papers)

# topic nodes   
def import_paper_topics(driver, file_path, cso_topics):
    papers = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            topics = extract_topics(row.get("title"), row.get("abstract"), cso_topics)
            if topics:
                papers.append({
                    "paperId": row["paperId"],
                    "topics": topics
                })
    
    query = """
    UNWIND $papers AS paper
    MATCH (p:Paper {paperId: paper.paperId})
    SET p.topics = paper.topics
    WITH p, paper
    UNWIND paper.topics AS topic
    MATCH (t:Topic {name: topic})
    MERGE (p)-[:IS_ABOUT]->(t)
    """
    with driver.session() as session:
        session.run(query, papers=papers)
 
# author nodes   
def import_authors_and_relations(driver, file_path):
    papers = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            papers.append({
                "paperId": row["paperId"],
                "authors": row.get("authors", "[]")
            })
    
    query = """
    UNWIND $papers AS row
    MATCH (p:Paper {paperId: row.paperId})
    WITH p, apoc.convert.fromJsonList(row.authors) AS authors
    UNWIND authors AS author
    MERGE (a:Author {authorId: author.authorId})
    SET a.name = author.name
    MERGE (p)-[:AUTHORED_BY]->(a)
    """
    with driver.session() as session:
        session.run(query, papers=papers)

# publication type nodes
def import_publication_types(driver, file_path):
    papers_data = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pub_types = row.get("publicationTypes", "")
            try:
                if isinstance(pub_types, str):
                    types_list = pub_types.split(";")
                    for type_name in types_list:
                        if type_name:
                            papers_data.append({
                                "paperId": row["paperId"],
                                "typeName": type_name.strip()
                            })
            except Exception as e:
                logger.warning(f"Error processing publicationTypes for paperId {row['paperId']}: {e}")

    query = """
    UNWIND $papers as row
    MERGE (pt:PublicationType {name: row.typeName})
    WITH pt, row
    MATCH (p:Paper {paperId: row.paperId})
    MERGE (p)-[:HAS_TYPE]->(pt)
    """
    with driver.session() as session:
        session.run(query, papers=papers_data)
        
# journal nodes       
def import_journals(driver, file_path):
    journals = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            journal_data = row.get("journal", "")
            if journal_data:
                try:
                    journal_info = json.loads(journal_data.replace("'", '"'))
                    
                    if journal_info.get("name"):
                        journals.append({
                            "paperId": row["paperId"],
                            "journalName": journal_info.get("name", ""),
                            "pages": journal_info.get("pages", ""),
                            "volume": journal_info.get("volume", "")
                        })
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in journal for paperId {row['paperId']}: {journal_data}")

    query = """
    UNWIND $journals as row
    MERGE (j:Journal {name: row.journalName})
    SET j.journalId = id(j),
        j.pages = row.pages,
        j.volume = row.volume
    WITH j, row
    MATCH (p:Paper {paperId: row.paperId})
    MERGE (p)-[:IN_JOURNAL]->(j)
    """

    with driver.session() as session:
        session.run(query, journals=journals)

# field of study nodes
def import_fields_of_study(driver, file_path):
    fields = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            s2_fields = row.get("s2FieldsOfStudy", "")
            if s2_fields:
                try:
                    fields_list = s2_fields.split(";")
                    for field in fields_list:
                        if field: 
                            fields.append({
                                "paperId": row["paperId"],
                                "fieldName": field.strip()
                            })
                except Exception as e:
                    logger.warning(f"Error processing s2FieldsOfStudy for paperId {row['paperId']}: {e}")
    
    query = """
    UNWIND $fields AS row
    MERGE (f:FieldOfStudy {name: row.fieldName})
    WITH f, row
    MATCH (p:Paper {paperId: row.paperId})
    MERGE (p)-[:HAS_FIELD]->(f)
    """
    with driver.session() as session:
        session.run(query, fields=fields)
        
def import_references(driver):
    query = f"""
    LOAD CSV WITH HEADERS FROM 'file:///{os.path.basename(REFERENCES_PATH)}' AS row
    MATCH (source:Paper {{paperId: row.source_id}})
    MATCH (target:Paper {{paperId: row.target_id}})
    MERGE (source)-[:REFERENCES]->(target)
    """
    with driver.session() as session:
        session.run(query)

def validate_graph(driver):
    with driver.session() as session:
        # Cek jumlah node
        paper_count = session.run("MATCH (p:Paper) RETURN count(p) AS count").single()["count"]
        topic_count = session.run("MATCH (t:Topic) RETURN count(t) AS count").single()["count"]
        author_count = session.run("MATCH (a:Author) RETURN count(a) AS count").single()["count"]
        publication_type_count = session.run("MATCH (pt:PublicationType) RETURN count(pt) AS count").single()["count"]
        field_of_study_count = session.run("MATCH (f:FieldOfStudy) RETURN count(f) AS count").single()["count"]
        journal_count = session.run("MATCH (j:Journal) RETURN count(j) AS count").single()["count"]
        
        # Cek paper dengan topik
        paper_topics = session.run("""
        MATCH (p:Paper)-[:IS_ABOUT]->(t:Topic)
        RETURN p.paperId AS paperId, p.title AS title, collect(t.name) AS topics
        LIMIT 1
        """)
        paper_topics = [record.data() for record in paper_topics]
        
        # Cek hierarki
        hierarchy = session.run("""
        MATCH (t1:Topic)-[:SUB_TOPIC_OF]->(t2:Topic)
        WHERE t2.name = 'computer_security'
        RETURN t1.name, t2.name
        LIMIT 10
        """)
        hierarchy = [record.data() for record in hierarchy]
    
    result = {
        "total_papers": paper_count,
        "total_topics": topic_count,
        "total_authors": author_count,
        "total_publication_type": publication_type_count,
        "total_fields_of_study": field_of_study_count,
        "journal_count": journal_count,
        "sample_paper_topics": [
            {
                "paperId": row["paperId"],
                "title": row["title"],
                "topics": row["topics"]
            } for row in paper_topics
        ],
        "sample_hierarchy": [
            {
                "child": row["t1.name"],
                "parent": row["t2.name"]
            } for row in hierarchy
        ]
    }
    return result

def import_to_neo4j(driver):
    logger.info("Memulai proses import ke Neo4j")
    
    #delete existing data
    clear_neo4j(driver)
    
    cso_topics, cso_hierarchy = parse_cso_rdf(CSO_RDF_PATH)
    topic_names = [topic["name"] for topic in cso_topics]
    
    # Parsing CSO dan generate graph
    import_cso_hierarchy(driver, cso_topics, cso_hierarchy)
    logger.info(f"Number of CSO topics: {len(cso_topics)}, Filtered hierarchy: {len(cso_hierarchy)}")
    logger.info("Hierarki CSO berhasil diimpor ke Neo4j")
    
    # Impor paper csv
    import_papers_nodes(driver, PAPERS_PATH)
    logger.info(f"Data paper dari {PAPERS_PATH} berhasil diimpor")
    
    # Relasi topic dan paper
    import_paper_topics(driver, PAPERS_PATH, topic_names)
    logger.info("Relasi paper-topic berhasil diimpor")
    
    # Impor author dan relasi
    import_authors_and_relations(driver, PAPERS_PATH)
    logger.info("Author dan relasi berhasil diimpor")
    
    # Impor publisher dan relasi
    import_journals(driver, PAPERS_PATH)
    logger.info(f"Data jurnal dari {PAPERS_PATH} berhasil diimpor")
    
    # Impor field of study dan relasi
    import_fields_of_study(driver, PAPERS_PATH)
    logger.info(f"Data field of study dari {PAPERS_PATH} berhasil diimpor")
    
    #impor publication type dan relasi
    import_publication_types(driver, PAPERS_PATH)
    logger.info(f"Data publication types dari {PAPERS_PATH} berhasil diimpor")
    
    # Impor paper references (opsional)
    # if os.path.exists(PAPER_REFERENCES_PATH):
    #     import_papers_nodes(driver, PAPER_REFERENCES_PATH, is_reference=True)
    
    # Impor references (opsional)
    # if os.path.exists(REFERENCES_PATH):
    #     import_references(driver)
    
    # Validasi
    validation_result = validate_graph(driver)
    logger.info("Validasi knowledge graph selesai")
    return validation_result

@csrf_exempt
def generate_knowledge_graph(request):
    driver = None
    try:
        if request.method != "GET":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        driver = get_neo4j_driver()
        
        # Impor data ke Neo4j dan validasi
        validation_result = import_to_neo4j(driver)

        # Hitung jumlah baris
        papers_count = count_csv_rows(PAPERS_PATH)
        paper_references_count = count_csv_rows(PAPER_REFERENCES_PATH)
        references_count = count_csv_rows(REFERENCES_PATH)

        return JsonResponse({
            "message": "Knowledge graph generated successfully",
            "papers_processed": papers_count,
            "paper_references_processed": paper_references_count,
            "references_processed": references_count,
            "validation": validation_result
        }, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if driver:
            driver.close()