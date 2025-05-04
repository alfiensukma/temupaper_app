from django.shortcuts import render, redirect, HttpResponse
from django.core.paginator import Paginator
from app.models import User, Paper, SavesPaperRel
from datetime import datetime
import logging
from neomodel import db
import json

logger = logging.getLogger(__name__)

def save_paper_list(request):
    if not request.session.get('user_id'):
        return redirect('login')

    try:
        search_query = request.GET.get('q', '')
        page_number = int(request.GET.get('page', 1))

        user_id = request.session.get('user_id')
        user = User.nodes.get(userId=user_id)

        fix_missing_timestamps(user_id)

        id_months = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }

        all_papers = list(user.saves_papers.all())
        saved_papers_data = []

        for paper in all_papers:
            try:
                rel = user.saves_papers.relationship(paper)
                saved_at = rel.saved_at if hasattr(rel, 'saved_at') else None

                if saved_at:
                    if isinstance(saved_at, float):
                        saved_at = datetime.fromtimestamp(saved_at)
                else:
                    saved_at = datetime.now()
                    try:
                        user.saves_papers.reconnect(paper, {'saved_at': saved_at})
                    except Exception as e:
                        logger.error(f"Error updating timestamp: {str(e)}")

                formatted_date = f"{saved_at.day} {id_months[saved_at.month]} {saved_at.year}"

                author_names = []
                try:
                    authors = list(paper.authored_by.all())
                    author_names = [author.name for author in authors]
                except Exception as e:
                    logger.error(f"Error getting authors for paper {paper.paperId}: {str(e)}")

                pub_date = paper.publicationDate
                
                try:
                    if isinstance(pub_date, str):
                        pub_date = datetime.strptime(pub_date, "%Y-%m-%d %H:%M:%S")
                    formatted_publication_date = f"{pub_date.day} {id_months[pub_date.month]} {pub_date.year}"
                except Exception:
                    formatted_publication_date = None

                saved_papers_data.append({
                    'paper': paper,
                    'paper_id': paper.paperId,
                    'title': paper.title or "Untitled Paper",
                    'abstract': paper.abstract,
                    'year': paper.year,
                    'doi': paper.doi,
                    'venue': paper.venue,
                    'saved_at': saved_at,
                    'formatted_date': formatted_date,
                    'date': pub_date,
                    'formatted_publication_date': formatted_publication_date,
                    'authors': author_names
                })
            except Exception as e:
                logger.error(f"Error processing paper {paper.paperId}: {str(e)}")

        saved_papers_data.sort(key=lambda x: x['saved_at'], reverse=True)

        paginator = Paginator(saved_papers_data, 10)
        page_obj = paginator.get_page(page_number)

        context = {
            "content_template": "save-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "papers": page_obj.object_list,
            "page_obj": page_obj,
            "search_query": search_query,
        }

        return render(request, "base.html", context)

    except Exception as e:
        logger.error(f"Error loading saved papers: {str(e)}")
        context = {
            "content_template": "save-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "error": "Terjadi kesalahan saat memuat karya ilmiah tersimpan."
        }
        return render(request, "base.html", context)


def remove_saved_paper(request, paper_id):
    if not request.session.get('user_id'):
        return redirect('login')
        
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            user = User.nodes.get(userId=user_id)
            paper = Paper.nodes.get(paperId=str(paper_id))

            user.saves_papers.disconnect(paper)
       
            request.session['message'] = "Karya ilmiah berhasil dihapus dari simpanan"
            
        except Exception as e:
            logger.error(f"Error removing saved paper: {str(e)}")
            request.session['error'] = "Gagal menghapus karya ilmiah dari simpanan"
 
    search_query = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    redirect_url = f"/save-paper-list/?page={page}"
    if search_query:
        redirect_url += f"&q={search_query}"
    
    return redirect(redirect_url)


def fix_missing_timestamps(user_id=None):
    """Fix missing timestamps in SAVES_PAPER relationships"""
    try:
        if user_id:
            query = """
            MATCH (u:User {userId: $userId})-[r:SAVES_PAPER]->(p:Paper)
            WHERE r.saved_at IS NULL
            SET r.saved_at = timestamp() / 1000.0
            RETURN count(r) as updated_count
            """
            results, _ = db.cypher_query(query, {"userId": user_id})
        else:
            query = """
            MATCH (u:User)-[r:SAVES_PAPER]->(p:Paper)
            WHERE r.saved_at IS NULL
            SET r.saved_at = timestamp() / 1000.0
            RETURN count(r) as updated_count
            """
            results, _ = db.cypher_query(query)
        
        updated_count = results[0][0]
        return updated_count
    except Exception as e:
        logger.error(f"Error fixing timestamps: {str(e)}")
        return -1