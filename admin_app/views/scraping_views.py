from admin_app.services.history_service import HistoryService
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import time

@csrf_exempt
def log_scraping_history(request):
    try:
        data = json.loads(request.body)
        topics = data.get('topics', [])
        results = data.get('results', [])
        has_success = data.get('success', False)
        
        if not has_success:
            return JsonResponse({"status": "skipped", "message": "No successful scraping to record"})
        
        history_service = HistoryService()
        
        history_record = history_service.add_history(
            operation_type="scraping",
            details={
                "topics": topics,
                "results": results,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            },
            status="success"
        )
        
        return JsonResponse({"status": "success", "history_id": history_record.get('id')})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)