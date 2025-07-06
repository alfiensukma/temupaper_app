from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import datetime
from itertools import groupby
from app.models import User, Paper
from app.utils.parse_indonesian_date import format_date_to_indonesian
import logging
import json

logger = logging.getLogger(__name__)

INDONESIAN_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

def save_paper_list(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return render(request, 'base.html', {
            'content_template': 'save-paper/index.html',
            'error': 'Sesi pengguna tidak valid. Silakan login kembali.'
        })

    try:
        user = User.nodes.get(userId=user_id)
        all_saved_papers = user.saves_papers.all()

        processed_papers = []
        for paper in all_saved_papers:
            rel = user.saves_papers.relationship(paper)
            saved_at = rel.saved_at if hasattr(rel, 'saved_at') else datetime.now()
            
            if isinstance(saved_at, float):
                saved_at = datetime.fromtimestamp(saved_at)
            elif isinstance(saved_at, str):
                try:
                    saved_at = datetime.strptime(saved_at, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    saved_at = datetime.now()
            saved_at_str = saved_at.strftime("%Y-%m-%d %H:%M:%S")

            paper_data = {
                "paperId": paper.paperId,
                "title": paper.title or "Judul Tidak Tersedia",
                "abstract": paper.abstract or "",
                "year": paper.year,
                "authors": [author.name for author in paper.authored_by.all()],
                "saved_at": saved_at_str,
                "publicationDate": paper.publicationDate,
                "formatted_publication_date": format_date_to_indonesian(paper.publicationDate, paper.year)
            }
            processed_papers.append(paper_data)

        all_papers = sorted(processed_papers, key=lambda x: datetime.strptime(x['saved_at'], '%Y-%m-%d %H:%M:%S'), reverse=True)
        total_paper_count = len(all_papers)

        search_query = request.GET.get('search_query', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')

        context = {
            'papers_json': json.dumps(all_papers),
            'total_paper_count': total_paper_count,
            'search_query': search_query,
            'start_date': start_date,
            'end_date': end_date,
            'current_path': request.path,
        }

        return render(request, 'base.html', {
            'content_template': 'save-paper/index.html',
            **context
        })

    except Exception as e:
        logger.error(f'Error in saved_paper_list view: {e}', exc_info=True)
        return render(request, 'base.html', {
            'content_template': 'save-paper/index.html',
            'error': 'Gagal memuat daftar artikel ilmiah tersimpan.'
        })

@require_POST
def remove_paper(request):
    try:
        data = json.loads(request.body)
        paper_id = data.get('paperId')
        user_id = request.session.get('user_id')
        if not user_id or not paper_id:
            return JsonResponse({'success': False, 'error': 'Sesi pengguna atau ID kertas tidak valid.'}, status=400)

        user = User.nodes.get(userId=user_id)
        paper = Paper.nodes.get(paperId=paper_id)
        user.saves_papers.disconnect(paper)
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error removing saved paper: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Gagal menghapus artikel ilmiah.'}, status=500)