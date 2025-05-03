from django_unicorn.components import UnicornView
from datetime import datetime
import logging
from app.utils.parse_indonesian_date import parse_indonesian_date

logger = logging.getLogger(__name__)

class DateRangePickerView(UnicornView):
    show_picker = False
    start_date = ""
    end_date = ""
    
    def mount(self):
        self.start_date = self.request.GET.get('start_date', '')
        self.end_date = self.request.GET.get('end_date', '')
        
    def format_neo4j_date(self, date_str):
        try:
            date_obj = datetime.strptime(date_str, "%d %B %Y")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Date parsing error: {e}")
            return None
    
    def apply_filter(self):
        if self.start_date and self.end_date:
            try:
                # Validate dates before submitting
                start_dt = parse_indonesian_date(self.start_date)
                end_dt = parse_indonesian_date(self.end_date)
                
                current_params = dict(self.request.GET)
                current_params.update({
                    'start_date': [self.start_date],
                    'end_date': [self.end_date]
                })

                if 'query' not in current_params:
                    current_params['query'] = ['']
                
                from urllib.parse import urlencode
                query_string = urlencode(current_params, doseq=True)
                
                logger.info(f"Redirecting with params: {query_string}")
                self.redirect(f"/search?{query_string}")
                
            except Exception as e:
                logger.error(f"Error applying date filter: {e}")