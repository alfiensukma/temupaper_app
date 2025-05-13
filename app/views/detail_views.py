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
                RETURN s AS similar_paper, r.score AS score
                ORDER BY r.score DESC
                LIMIT 5
                """,
                paperId=paper_id
            )

            # Iterasi hasil query
            for record in result:
                similar_paper_node = record["similar_paper"]
                similarity_score = record["score"]
                
                # Pastikan kita mengakses properti paperId dengan benar
                try:
                    similar_paper_id = similar_paper_node.get("paperId")
                    if not similar_paper_id:
                        # Cek jika property diakses dengan cara berbeda di Neo4j
                        if hasattr(similar_paper_node, "id") and similar_paper_node.id:
                            similar_paper_id = similar_paper_node.id
                        else:
                            logger.error(f"Cannot extract paperId from Neo4j node: {similar_paper_node}")
                            continue
                            
                    # Ambil paper lengkap dari database dengan neomodel
                    paper_obj = Paper.nodes.get(paperId=similar_paper_id)
                    
                    # Ambil author
                    authors = []
                    for author in paper_obj.authored_by.all():
                        authors.append({
                            "name": author.name
                        })
                    
                    # Buat data paper
                    paper_data = {
                        "paperId": paper_obj.paperId,
                        "title": paper_obj.title,
                        "abstract": paper_obj.abstract,
                        "score": similarity_score,
                        "authors": authors,
                        "date": paper_obj.publicationDate,
                        "doi": paper_obj.doi,
                        "url": paper_obj.url,
                        "year": paper_obj.year
                    }
                    
                    # Format tanggal
                    if paper_data["date"]:
                        try:
                            try:
                                dt = datetime.strptime(paper_data["date"], "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                dt = datetime.strptime(paper_data["date"], "%Y-%m-%d")
                            paper_data["date"] = dt.strftime("%d %B %Y")
                        except Exception as e:
                            logger.error(f"Date parse error for paper {paper_data['paperId']}: {e}")
                            paper_data["date"] = paper_data.get("year", "Unknown date")
                    else:
                        paper_data["date"] = paper_data.get("year", "Unknown date")
                    
                    # Tambahkan ke hasil
                    paper_recommendation.append(paper_data)
                
                except Paper.DoesNotExist:
                    logger.error(f"Paper with ID {similar_paper_id} does not exist.")
                    continue
                except Exception as e:
                    logger.error(f"Error processing paper: {str(e)}")
                    continue
        
        return paper_recommendation
    
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
                try:
                    dt = datetime.strptime(data_paper["date"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    dt = datetime.strptime(data_paper["date"], "%Y-%m-%d")
                data_paper["date"] = dt.strftime("%d %B %Y")
            except Exception as e:
                logger.error(f"Date parse error for paper {data_paper['paperId']}: {e}")
                data_paper["date"] = data_paper.get("year", "Unknown date")
        else:
            data_paper["date"] = data_paper.get("year", "Unknown date")

        # Dapatkan rekomendasi paper
        paper_recommendation = get_recommendation(paper_id)

        return render(request, "base.html", {
            "content_template": "detail-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "paper": data_paper,
            "paper_recommendation": paper_recommendation
        })

    except Paper.DoesNotExist:
        logger.error(f"Paper with ID {paper_id} not found")
        return render(request, "base.html", {
            "content_template": "detail-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "error": f"Paper not found"
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