from django.shortcuts import render, redirect
from app.decorators import login_required, admin_required
from app.utils.neo4j_connection import Neo4jConnection
import logging

logger = logging.getLogger(__name__)

@admin_required
def admin_dashboard(request):
    context = {
        'active_menu': 'dashboard',
        'paper_count': 0,
        'user_count': 0,
        'last_import': None,
    }
    
    try:
        conn = Neo4jConnection().get_driver()
        with conn.session() as session:
            paper_result = session.run("MATCH (p:Paper) RETURN count(p) AS count")
            context['paper_count'] = paper_result.single()["count"]
            
            user_result = session.run("MATCH (u:User) WHERE u.role_id <> 1 RETURN count(u) AS count")
            context['user_count'] = user_result.single()["count"]
            
            import_result = session.run("""
                MATCH (h:History) 
                WHERE h.operation_type = 'import' AND h.status = 'success'
                RETURN h
                ORDER BY h.timestamp DESC
                LIMIT 1
            """)
            
            import_record = import_result.single()
            if import_record:
                import_data = dict(import_record["h"])
                try:
                    import ast
                    import_data["details"] = ast.literal_eval(import_data["details"])
                except:
                    import_data["details"] = {}
                
                # Format the timestamp
                try:
                    from datetime import datetime
                    timestamp = datetime.fromisoformat(import_data["timestamp"].replace('Z', '+00:00'))
                    import_data["formatted_date"] = timestamp.strftime("%d %b %Y, %H:%M")
                except:
                    import_data["formatted_date"] = import_data["timestamp"]
                
                context['last_import'] = import_data
            
    except Exception as e:
        logger.error(f"Error fetching data from Neo4j: {str(e)}")
        context['error'] = "Gagal mengambil jumlah karya ilmiah atau pengguna"
    finally:
        conn.close()

    return render(request, 'dashboard/index.html', context)
