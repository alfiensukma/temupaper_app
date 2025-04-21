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
    
    print("Available namespaces in graph:")
    for prefix, ns in g.namespaces():
        print(f"{prefix}: {ns}")

    hierarchy = []
    topic_labels = {}

    # Ekstraksi topik dan label
    # Loop label (untuk mapping URI -> label)
    for s, p, o in g.triples((None, RDFS.label, None)):
        topic_uri = str(s)
        label = str(o).lower().replace(' ', '_')
        topic_labels[topic_uri] = label

    # Loop hierarchy (untuk parent-child topic)
    for s, p, o in g.triples((None, CSO.superTopicOf, None)):
        parent_uri = str(s)
        child_uri = str(o)
        parent = topic_labels.get(parent_uri, parent_uri.split('/')[-1]).lower().replace(' ', '_')
        child = topic_labels.get(child_uri, child_uri.split('/')[-1]).lower().replace(' ', '_')
        hierarchy.append((child, parent))
    
    logger.info(f"Total triples in RDF: {len(g)}")
    logger.info(f"Total hierarchy relations found: {len(hierarchy)}")
    logger.info(f"First few: {hierarchy[:5]}")
        
    # Batasi hierarki hingga 4 tingkat
    filtered_hierarchy = []
    level_map = {'computer_science': 1} 
    processed = set()

    # Iterasi berulang untuk memastikan semua level diproses
    while True:
        added = False
        for child, parent in hierarchy:
            if (child, parent) in processed:
                continue
            parent_level = level_map.get(parent)
            if parent_level is not None and parent_level < 4:
                filtered_hierarchy.append((child, parent))
                level_map[child] = parent_level + 1
                processed.add((child, parent))
                added = True
        if not added:
            break
        
    topics = set()
    for child, parent in filtered_hierarchy:
        topics.add(child)
        topics.add(parent)
    
    logger.info(f"Filtered hierarchy relations: {len(filtered_hierarchy)}")
    logger.info(f"Total topics after filtering: {len(topics)}")
    
    root_candidates = set(parent for _, parent in filtered_hierarchy)
    print("Root candidates:", list(root_candidates)[:20])

    return list(topics), filtered_hierarchy

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
                    if similarity > 0.8:  # Threshold
                        topics.add(topic)
                        break
    
    return list(topics)

def import_cso_hierarchy(driver, topics, hierarchy):
    query_topics = """
    UNWIND $topics AS topic
    MERGE (t:Topic {name: topic})
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

# Pre-process paper untuk ekstrak topik dan author
def import_papers_nodes(driver, file_path, is_reference=False):
    papers = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            papers.append({
                "paperId": row["paperId"],
                "title": row.get("title", ""),
                "abstract": row.get("abstract", ""),
                "corpusId": row.get("corpusId", ""),
                "externalIds": row.get("externalIds", ""),
                "authors": row.get("authors", "[]"),
                "year": row.get("year", ""),
                "url": row.get("url", ""),
                "publicationDate": row.get("publicationDate", ""),
                "fieldsOfStudy": row.get("fieldsOfStudy", ""),
                "s2FieldsOfStudy": row.get("s2FieldsOfStudy", ""),
                "venue": row.get("venue", ""),
                "publicationVenue": row.get("publicationVenue", ""),
                "citationCount": row.get("citationCount", ""),
                "influentialCitationCount": row.get("influentialCitationCount", ""),
                "publicationTypes": row.get("publicationTypes", ""),
                "journal": row.get("journal", ""),
                "citationStyles": row.get("citationStyles", ""),
                "embedding": row.get("embedding", ""),
                "referenceCount": row.get("referenceCount", ""),
                "reference_id": row.get("reference_id", "")
            })
    
    query = f"""
    UNWIND $papers AS row
    MERGE (p:Paper {{paperId: row.paperId}})
    SET p.corpusId = row.corpusId,
        p.externalIds = row.externalIds,
        p.title = row.title,
        p.authors = [author IN apoc.convert.fromJsonList(row.authors) | author.name],
        p.year = toInteger(row.year),
        p.abstract = row.abstract,
        p.url = row.url,
        p.publicationDate = row.publicationDate,
        p.fieldsOfStudy = split(row.fieldsOfStudy, ';'),
        p.s2FieldsOfStudy = split(row.s2FieldsOfStudy, ';'),
        p.venue = row.venue,
        p.publicationVenue = row.publicationVenue,
        p.citationCount = toInteger(row.citationCount),
        p.influentialCitationCount = toInteger(row.influentialCitationCount),
        p.publicationTypes = split(row.publicationTypes, ';'),
        p.journal = row.journal,
        p.citationStyles = row.citationStyles,
        p.embedding = apoc.convert.fromJsonList(row.embedding)
    {'SET p.reference_id = split(row.reference_id, ";")' if not is_reference else ''}
    """
    with driver.session() as session:
        session.run(query, papers=papers)
    
def import_paper_topics(driver, file_path, cso_topics):
    papers = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            topics = extract_topics(row.get("title"), row.get("abstract"), cso_topics)
            papers.append({
                "paperId": row["paperId"],
                "cso_topics": topics
            })
    
    query = """
    UNWIND $papers AS row
    MATCH (p:Paper {paperId: row.paperId})
    SET p.cso_topics = row.cso_topics
    WITH p, row
    FOREACH (topic IN row.cso_topics |
        MERGE (t:Topic {name: topic})
        MERGE (p)-[:IS_ABOUT]->(t)
    )
    """
    with driver.session() as session:
        session.run(query, papers=papers)
    
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
    MERGE (p)-[:WRITTEN_BY]->(a)
    """
    with driver.session() as session:
        session.run(query, papers=papers)

def import_references(driver):
    query = f"""
    LOAD CSV WITH HEADERS FROM 'file:///{os.path.basename(REFERENCES_PATH)}' AS row
    MATCH (source:Paper {{paperId: row.source_id}})
    MATCH (target:Paper {{paperId: row.target_id}})
    MERGE (source)-[:REFERENCES]->(target)
    """
    with driver.session() as session:
        session.run(query)

def import_publishers(driver, file_path):
    publishers = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            publication_venue = row.get("publicationVenue", "")
            if publication_venue:
                try:
                    venue_data = json.loads(publication_venue.replace("'", '"'))
                    publisher_name = venue_data.get("name", "")
                    if publisher_name:
                        publishers.append({
                            "paperId": row["paperId"],
                            "publisherName": publisher_name
                        })
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in publicationVenue for paperId {row['paperId']}: {publication_venue}")
    
    query = """
    UNWIND $publishers AS row
    MATCH (p:Paper {paperId: row.paperId})
    MERGE (pub:Publisher {name: row.publisherName})
    MERGE (p)-[:PUBLISHED_BY]->(pub)
    """
    with driver.session() as session:
        session.run(query, publishers=publishers)

def import_fields_of_study(driver, file_path):
    fields = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            s2_fields = row.get("s2FieldsOfStudy", "")
            if s2_fields:
                try:
                    fields_list = ast.literal_eval(s2_fields)
                    for field in fields_list:
                        if field:
                            fields.append({
                                "paperId": row["paperId"],
                                "fieldName": field
                            })
                except (ValueError, SyntaxError):
                    logger.warning(f"Invalid s2FieldsOfStudy format for paperId {row['paperId']}: {s2_fields}")
    
    query = """
    UNWIND $fields AS row
    MATCH (p:Paper {paperId: row.paperId})
    MERGE (f:FieldOfStudy {name: row.fieldName})
    MERGE (p)-[:HAS_FIELD]->(f)
    """
    with driver.session() as session:
        session.run(query, fields=fields)

def validate_graph(driver):
    with driver.session() as session:
        # Cek jumlah node
        paper_count = session.run("MATCH (p:Paper) RETURN count(p) AS count").single()["count"]
        topic_count = session.run("MATCH (t:Topic) RETURN count(t) AS count").single()["count"]
        author_count = session.run("MATCH (a:Author) RETURN count(a) AS count").single()["count"]
        publisher_count = session.run("MATCH (p:Publisher) RETURN count(p) AS count").single()["count"]
        field_of_study_count = session.run("MATCH (f:FieldOfStudy) RETURN count(f) AS count").single()["count"]
        
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
        "total_publishers": publisher_count,
        "total_fields_of_study": field_of_study_count,
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
    #clear_neo4j(graph)
    
    cso_topics, cso_hierarchy = parse_cso_rdf(CSO_RDF_PATH)
    
    # Parsing CSO dan generate graph
    #import_cso_hierarchy(driver, cso_topics, cso_hierarchy)
    logger.info(f"Number of CSO topics: {len(cso_topics)}, Filtered hierarchy: {len(cso_hierarchy)}")
    logger.info("Hierarki CSO berhasil diimpor ke Neo4j")
    
    # Impor paper csv
    #import_papers_nodes(driver, PAPERS_PATH)
    logger.info(f"Data paper dari {PAPERS_PATH} berhasil diimpor")
    
    # Relasi topic dan paper
    #import_paper_topics(driver, PAPERS_PATH, cso_topics)
    logger.info("Relasi paper-topic berhasil diimpor")
    
    # Impor author dan relasi
    # import_authors_and_relations(driver, PAPERS_PATH)
    logger.info("Author dan relasi berhasil diimpor")
    
    # Impor publisher dan relasi
    # import_publishers(driver, PAPERS_PATH)
    logger.info(f"Data publisher dari {PAPERS_PATH} berhasil diimpor")
    
    # Impor field of study dan relasi
    # import_fields_of_study(driver, PAPERS_PATH)
    logger.info(f"Data field of study dari {PAPERS_PATH} berhasil diimpor")
    
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