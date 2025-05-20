from django.shortcuts import render, redirect
from django.http import JsonResponse
from app.utils.neo4j_connection import Neo4jConnection
from dotenv import load_dotenv
import logging
from datetime import datetime
from app.models import User, Paper


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

def get_recommendation(paper_id):
    paper_recommendation = []  # Inisialisasi list di awal
    
    try:
        neo4j_connection = Neo4jConnection()
        driver = neo4j_connection.get_driver()  
        
        with driver.session() as session:
            # Ambil paper yang mirip
            result = session.run(
                """
                MATCH (p:Paper {paperId: $paperId})-[r:SIMILAR]->(s:Paper)
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                RETURN 
                    s.title AS title,
                    s.paperId AS paperId,
                    s.abstract AS abstract,
                    s.publicationDate AS date,
                    s.year AS year,
                    s.pagerank AS pagerank, 
                    r.score AS score,
                    collect(DISTINCT author.name) AS authors
                ORDER BY r.score DESC
                LIMIT 5
                """,
                paperId=paper_id
            )

            papers = [{
                "paperId": record["paperId"],
                "title": record["title"],
                "date": record["date"],
                "abstract": record["abstract"],
                "authors": record["authors"],
                "year": record["year"]
            } for record in result]

            for paper in papers:
                if paper["date"]:
                    try:
                        date_str = paper["date"]
                        # Format "m/d/yyyy 0:00" atau "m/d/yyyy"
                        if '/' in date_str:
                            date_str = date_str.split()[0]
                            month, day, year = map(int, date_str.split('/'))
                            dt = datetime(year, month, day)
                            paper["date"] = dt.strftime("%d %B %Y")
                        # Format "yyyy-mm-dd"
                        elif '-' in date_str:
                            dt = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                            paper["date"] = dt.strftime("%d %B %Y")
                        else:
                            paper["date"] = paper["year"]
                    except Exception as e:
                        logger.error(f"Error formatting date '{paper['date']}': {str(e)}")
                        paper["date"] = paper["date"]

        if driver:
            driver.close()   
        return papers
        
    
    except Exception as e:
        logger.error(f"Error in get_recommendation: {str(e)}")
        return []
    finally:
        # Pastikan driver didefinisikan sebelum mencoba menutupnya
        if 'driver' in locals() and driver is not None:
            driver.close()

def get_detail_paper(request, paper_id):
    if not paper_id:
        return JsonResponse({'error': 'Missing paper_id'}, status=400)

    try:
        paper = Paper.nodes.get(paperId=paper_id)

        authors = []
        for author in paper.authored_by.all():
            authors.append({
                "name": author.name
            })

        data_paper = {
            "paperId": paper.paperId,
            "title": paper.title,
            "abstract": paper.abstract,
            "date": paper.publicationDate,
            "doi": paper.doi,
            "url": paper.url,
            "year": paper.year,
            "authors": authors
        }

        if data_paper["date"]:
            try:
                date_str = data_paper["date"]
                # Format "m/d/yyyy 0:00" atau "m/d/yyyy"
                if '/' in date_str:
                    date_str = date_str.split()[0]
                    month, day, year = map(int, date_str.split('/'))
                    dt = datetime(year, month, day)
                    data_paper["date"] = dt.strftime("%d %B %Y")
                # Format "yyyy-mm-dd"
                elif '-' in date_str:
                    dt = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                    data_paper["date"] = dt.strftime("%d %B %Y")
                else:
                    data_paper["date"] = data_paper["year"]
            except Exception as e:
                logger.error(f"Error formatting date '{paper['date']}': {str(e)}")
                data_paper["date"] = data_paper["date"]

        # Dapatkan rekomendasi paper
        paper_recommendation = get_recommendation(paper_id)

        return render(request, "base.html", {
            "content_template": "detail-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "paper": data_paper,
            "paper_recommendation": paper_recommendation
        })

    except Exception as e:
        logger.error(f"Error getting paper detail: {str(e)}")
        return render(request, "base.html", {
            "content_template": "detail-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "error": f"An error occurred: {str(e)}"
        })


def record_paper_read(request):
    if request.method == 'POST':
        paper_id = request.POST.get('paper_id')
        access_method = request.POST.get('access_method')

        user_id = request.session.get('user_id', '')
        
        logger.info(f"Recording paper read - User ID: {user_id}, Paper ID: {paper_id}, Access Method: {access_method}")
        
        if not user_id:
            return JsonResponse({'status': 'error', 'message': 'User not authenticated'}, status=401)
        
        if not paper_id:
            return JsonResponse({'status': 'error', 'message': 'Missing paper_id'}, status=400)
        
        try:
            user = User.nodes.get(userId=user_id)
            paper = Paper.nodes.get(paperId=paper_id)

            existing_relations = list(user.has_read.all_relationships(paper))
            
            if existing_relations:
                rel = existing_relations[0]
                rel.read_at = datetime.now()
                rel.access_method = access_method
                rel.save()
                logger.info(f"Updated existing read relationship")
            else:
                user.has_read.connect(paper, {
                    'read_at': datetime.now(),
                    'access_method': access_method
                })
                logger.info(f"Created new read relationship")
            
            return JsonResponse({'status': 'success', 'message': 'Paper read recorded'})
        
        except User.DoesNotExist:
            logger.error(f"User not found with ID: {user_id}")
            return JsonResponse({'status': 'error', 'message': f'User not found with ID: {user_id}'}, status=404)
        except Paper.DoesNotExist:
            logger.error(f"Paper not found with ID: {paper_id}")
            return JsonResponse({'status': 'error', 'message': f'Paper not found with ID: {paper_id}'}, status=404)
        except Exception as e:
            logger.error(f"Error recording paper read: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)