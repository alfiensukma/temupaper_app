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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CSV_DIR = os.path.join(BASE_DIR, "data-csv")
PAPERS_PATH = os.path.join(DATA_CSV_DIR, "papers.csv")
JOURNALS_PATH = os.path.join(DATA_CSV_DIR, "journalss.csv")
INSTITUTION_PATH = os.path.join(DATA_CSV_DIR, "perguruan-tinggi.csv")
REFERENCES_PATH = os.path.join(DATA_CSV_DIR, "references.csv")

def count_csv_rows(file_path):
    if not os.path.exists(file_path):
        return 0
    with open(file_path, mode='r', encoding='utf-8') as f:
        return sum(1 for row in csv.DictReader(f))

def clear_neo4j(driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

def import_journal_nodes(driver, file_path):
    journals = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            issn = row.get("Issn", "")
            issn_list = issn.split(", ")
            for issn in issn_list:
                journals.append({
                    "title": row["Title"],
                    "sjr": row["SJR"],
                    "rank": row["SJR Best Quartile"],
                    "issn": issn
                })
    
    query = """
    UNWIND $journals AS row
    MERGE (j:Journal {issn: row.issn})
        SET j.title = row.title,
            j.sjr = row.sjr,
            j.rank = row.rank
    """
    with driver.session() as session:
        session.run(query, journals=journals)

#Impor perguruan tinggi
def import_institusi_nodes(driver, file_path):
    institusi = []
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            institusi.append({
                "names": row["universitas"],
                "institutionId": row["no"],
            })
                
    
    query = """
    UNWIND $institusi AS row
    MERGE (pt:Institution {institutionId: row.institutionId})
        SET pt.names = row.names
    """
    with driver.session() as session:
        session.run(query, institusi=institusi)

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
# def import_paper_topics(driver, file_path, cso_topics):
#     papers = []
#     with open(file_path, mode='r', encoding='utf-8') as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             topics = extract_topics(row.get("title"), row.get("abstract"), cso_topics)
#             if topics:
#                 papers.append({
#                     "paperId": row["paperId"],
#                     "topics": topics
#                 })
    
#     query = """
#     UNWIND $papers AS paper
#     MATCH (p:Paper {paperId: paper.paperId})
#     SET p.topics = paper.topics
#     WITH p, paper
#     UNWIND paper.topics AS topic
#     MATCH (t:Topic {name: topic})
#     MERGE (p)-[:IS_ABOUT]->(t)
#     """
#     with driver.session() as session:
#         session.run(query, papers=papers)
 
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
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            journal_data = row.get("journal", "")
            publication = row.get("publicationVenue", "")
            paper_id = row.get("paperId", "")
            
            if not journal_data and not publication:
                continue
                
            try:
                journal_info = {}
                if journal_data:
                    # Cek apakah journal_data sudah berbentuk dictionary
                    if isinstance(journal_data, dict):
                        journal_info = journal_data
                    else:
                        # Jika string, coba parse sebagai JSON
                        journal_info = json.loads(journal_data.replace("'", '"'))
                
                # Periksa dan parse data publication
                publication_info = {}
                if publication:
                    # Cek apakah publication sudah berbentuk dictionary
                    if isinstance(publication, dict):
                        publication_info = publication
                    else:
                        # Jika string, coba parse sebagai JSON
                        publication_info = json.loads(publication.replace("'", '"'))
                
                journal_node_id = None
                
                # 1. Periksa ISSN utama - dengan normalisasi format (hapus strip)
                if publication_info.get("issn"):
                    issn = publication_info.get("issn", "")
                    normalized_issn = issn.replace("-", "")  # Hapus strip
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (j:Journal {issn: $issn})
                            RETURN id(j) as nodeId
                        """, issn=normalized_issn)
                        record = result.single()
                        if record:
                            journal_node_id = record["nodeId"]
                
                # 2. Jika ISSN utama tidak ada, periksa alternate_issns
                if journal_node_id is None and publication_info.get("alternate_issns"):
                    alternate_issns = publication_info.get("alternate_issns")
                    
                    # Jika alternate_issns dalam bentuk string, konversi ke list
                    if isinstance(alternate_issns, str):
                        alternate_issns = json.loads(alternate_issns.replace("'", '"'))
                    
                    for alt_issn in alternate_issns:
                        normalized_alt_issn = alt_issn.replace("-", "")  # Hapus strip
                        with driver.session() as session:
                            result = session.run("""
                                MATCH (j:Journal {issn: $issn})
                                RETURN id(j) as nodeId
                            """, issn=normalized_alt_issn)
                            record = result.single()
                            if record:
                                journal_node_id = record["nodeId"]
                                break
                
                # 3. Jika masih tidak ditemukan, periksa dengan nama
                if journal_node_id is None:
                    journal_name = None
                    
                    # Cek name dari journal_info
                    if journal_info and journal_info.get("name"):
                        journal_name = journal_info.get("name")
                    # Jika tidak ada, cek name dari publication_info
                    elif publication_info and publication_info.get("name"):
                        journal_name = publication_info.get("name")
                    
                    if journal_name:
                        with driver.session() as session:
                            result = session.run("""
                                MATCH (j:Journal {name: $name})
                                RETURN id(j) as nodeId
                            """, name=journal_name)
                            record = result.single()
                            if record:
                                journal_node_id = record["nodeId"]
                
                # 4. Buat relasi jika journal ditemukan
                if journal_node_id is not None:
                    with driver.session() as session:
                        session.run("""
                            MATCH (p:Paper {paperId: $paperId})
                            MATCH (j:Journal) WHERE id(j) = $journalId
                            MERGE (p)-[:IN_JOURNAL]->(j)
                        """, paperId=paper_id, journalId=journal_node_id)
            
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in journal for paperId {paper_id}: {journal_data}")

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
        author_count = session.run("MATCH (a:Author) RETURN count(a) AS count").single()["count"]
        publication_type_count = session.run("MATCH (pt:PublicationType) RETURN count(pt) AS count").single()["count"]
        field_of_study_count = session.run("MATCH (f:FieldOfStudy) RETURN count(f) AS count").single()["count"]
        journal_count = session.run("MATCH (j:Journal) RETURN count(j) AS count").single()["count"]
        institution_count = session.run("MATCH (j:Institution) RETURN count(j) AS count").single()["count"]
    
    result = {
        "total_papers": paper_count,
        "total_authors": author_count,
        "total_publication_type": publication_type_count,
        "total_fields_of_study": field_of_study_count,
        "journal_count": journal_count,
        "institution_count": institution_count
    }
    return result

def import_to_neo4j(driver):
    logger.info("Memulai proses import ke Neo4j")
    
    #delete existing data
    clear_neo4j(driver)

    #Impor institusi
    import_institusi_nodes(driver, INSTITUTION_PATH)
    logger.info(f"Data institusi dari {INSTITUTION_PATH} berhasil diimpor")

    #Impor journal (Scimago)
    import_journal_nodes(driver, JOURNALS_PATH)
    logger.info(f"Data jurnal dari {JOURNALS_PATH} berhasil diimpor")
    
    # Impor paper csv
    import_papers_nodes(driver, PAPERS_PATH)
    logger.info(f"Data paper dari {PAPERS_PATH} berhasil diimpor")
    
    # Impor author dan relasi
    import_authors_and_relations(driver, PAPERS_PATH)
    logger.info("Author dan relasi berhasil diimpor")
    
    # # Impor publisher dan relasi
    import_journals(driver, PAPERS_PATH)
    logger.info(f"Data relasi jurnal dari {PAPERS_PATH} berhasil diimpor")
    
    # Impor field of study dan relasi
    import_fields_of_study(driver, PAPERS_PATH)
    logger.info(f"Data field of study dari {PAPERS_PATH} berhasil diimpor")
    
    #impor publication type dan relasi
    import_publication_types(driver, PAPERS_PATH)
    logger.info(f"Data publication types dari {PAPERS_PATH} berhasil diimpor")
    
    # # Impor paper references (opsional)
    # # if os.path.exists(PAPER_REFERENCES_PATH):
    # #     import_papers_nodes(driver, PAPER_REFERENCES_PATH, is_reference=True)
    
    # # Impor references (opsional)
    # # if os.path.exists(REFERENCES_PATH):
    # #     import_references(driver)
    
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
        # paper_references_count = count_csv_rows(PAPER_REFERENCES_PATH)
        # references_count = count_csv_rows(REFERENCES_PATH)

        return JsonResponse({
            "message": "Knowledge graph generated successfully",
            "papers_processed": papers_count,
            # "paper_references_processed": paper_references_count,
            # "references_processed": references_count,
            "validation": validation_result
        }, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if driver:
            driver.close()