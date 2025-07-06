from django.shortcuts import render
from app.decorators import admin_required
from app.utils.neo4j_connection import Neo4jConnection
from neomodel import db
import logging
import ast
from datetime import datetime

logger = logging.getLogger(__name__)

@admin_required
def admin_dashboard(request):
    context = {
        'active_menu': 'dashboard',
        'paper_count': 0,
        'user_count': 0,
        'last_import': None,
        'error': None
    }
    conn = None
    try:
        conn = Neo4jConnection()
        driver = conn.get_driver()
        with driver.session() as session:
            paper_result = session.run("MATCH (p:Paper) RETURN count(p) AS count")
            context['paper_count'] = paper_result.single()["count"]
            
            user_result = session.run("MATCH (u:User)-[:HAS_ROLE]->(r:Role {nama: 'User'}) RETURN count(u) AS count")
            context['user_count'] = user_result.single()["count"]

            import_result = session.run("""
                MATCH (h:History) 
                WHERE h.operation_type = 'import' AND h.status = 'success'
                RETURN h ORDER BY h.timestamp DESC LIMIT 1
            """)
            
            import_record = import_result.single()
            if import_record:
                import_data = dict(import_record["h"])
                try:
                    import_data["details"] = ast.literal_eval(import_data["details"])
                except:
                    import_data["details"] = {}
                
                try:
                    timestamp = datetime.fromisoformat(import_data["timestamp"].replace('Z', '+00:00'))
                    import_data["formatted_date"] = timestamp.strftime("%d %b %Y, %H:%M")
                except:
                    import_data["formatted_date"] = import_data["timestamp"]
                
                context['last_import'] = import_data
            
    except Exception as e:
        logger.error(f"Error fetching data for admin dashboard: {str(e)}")
        context['error'] = "Gagal mengambil data dari database. Pastikan koneksi, kredensial, dan layanan Neo4j sudah benar."
    finally:
        if conn:
            conn.close()
            
    return render(request, 'dashboard/index.html', context)

