from django.shortcuts import render, redirect
from app.decorators import login_required, admin_required
from app.models import Paper
from django.http import JsonResponse
from app.utils.neo4j_connection import Neo4jConnection
from datetime import datetime
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)

class PaperTableService:
    def __init__(self, session):
        self.session = session

    def parse_date(self, date_str, year=None):
        if not date_str and year:
            return str(year)
        if not date_str:
            return "-"
        try:
            # Format "m/d/yyyy" or "m/d/yyyy 0:00"
            if '/' in date_str:
                date_str = date_str.split()[0]
                month, day, year_val = map(int, date_str.split('/'))
                dt = datetime(year_val, month, day)
                return dt.strftime("%d %B %Y")
            # Format "yyyy-mm-dd"
            elif '-' in date_str:
                dt = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                return dt.strftime("%d %B %Y")
            else:
                return date_str
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return date_str

    def fetch_papers(self, search_value, order_field, order_dir, start, length):
        cypher = f"""
            MATCH (p:Paper)
            {f"WHERE toLower(p.title) CONTAINS toLower($search)" if search_value else ""}
            RETURN p
            ORDER BY p.{order_field} {'DESC' if order_dir == 'desc' else 'ASC'}
            SKIP $start LIMIT $length
        """
        params = {
            "search": search_value,
            "start": start,
            "length": length
        }
        result = self.session.run(cypher, **params)
        return [record['p'] for record in result]

    def count_papers(self, search_value):
        if search_value:
            cypher = "MATCH (p:Paper) WHERE toLower(p.title) CONTAINS toLower($search) RETURN count(p) as total"
            params = {"search": search_value}
        else:
            cypher = "MATCH (p:Paper) RETURN count(p) as total"
            params = {}
        return self.session.run(cypher, **params).single()['total']

    def to_datatable_row(self, idx, paper):
        title = paper.get('title', '')
        publication_date = paper.get('publicationDate', '') or paper.get('date', '')
        year = paper.get('year', None)
        tanggal = self.parse_date(publication_date, year)
        return {
            'no': idx,
            'judul': title,
            'tanggal': tanggal if tanggal else "-",
            'aksi': f'<button type="button" class="btn btn-danger btn-sm deleteBtn" data-paper-id="{paper.get("paperId","")}">'
                f'<i class="fas fa-trash-alt"></i></button>'
        }

@admin_required
def kelola_karya_ilmiah(request):
    return render(request, 'karya-ilmiah/index.html')

@admin_required
def datatable_paper_json(request):
    try:
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '').strip()
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_dir = request.GET.get('order[0][dir]', 'asc')

        columns = ['no', 'title', 'publicationDate', 'aksi']
        order_field = columns[order_column_index]
        if order_field in ['no', 'aksi']:
            order_field = 'title'

        conn = Neo4jConnection().get_driver()
        session = conn.session()
        service = PaperTableService(session)

        total = service.count_papers(search_value)
        papers = service.fetch_papers(search_value, order_field, order_dir, start, length)

        data = [
            service.to_datatable_row(idx, paper)
            for idx, paper in enumerate(papers, start=start+1)
        ]

        session.close()
        conn.close()

        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in datatable_paper_json: {e}")
        return JsonResponse({
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
@admin_required
def delete_paper(request):
    try:
        data = json.loads(request.body)
        paper_id = data.get('paperId')
        if not paper_id:
            return JsonResponse({'success': False, 'message': 'Paper ID tidak ditemukan'}, status=400)

        conn = Neo4jConnection().get_driver()
        session = conn.session()
        session.run("MATCH (p:Paper {paperId: $paperId}) DETACH DELETE p", paperId=paper_id)
        session.close()
        conn.close()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
@admin_required
def manage_paper(request):
    return render(request, 'karya-ilmiah/manage-paper.html')

@admin_required
def scraping_view(request):
    return render(request, 'karya-ilmiah/scraping.html')