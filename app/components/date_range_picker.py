from django_unicorn.components import UnicornView
from typing import List
import logging

from app.components.search_result import PaperProcessor

logger = logging.getLogger(__name__)

class DateRangePickerView(UnicornView):
    start_date: str = ""
    end_date: str = ""
    years: List[int] = []
    error_message: str = ""

    def mount(self):
        """Initialize component."""
        self.years = list(range(2025, 2019, -1))
        if hasattr(self.parent, 'request'):
            self.start_date = str(self.parent.request.session.get('start_date', '') or '')
            self.end_date = str(self.parent.request.session.get('end_date', '') or '')

    def apply_filter(self):
        try:
            logger.info(f"Received apply_filter: start_date={self.start_date}, end_date={self.end_date}")
            if self.start_date and self.end_date:
                start_year = int(self.start_date)
                end_year = int(self.end_date)
                if start_year > end_year:
                    self.error_message = "Tahun awal tidak boleh lebih besar dari tahun akhir"
                    logger.warning(f"Invalid year range: {start_year} > {end_year}")
                    return

            self.request.session['start_date'] = str(self.start_date or '')
            self.request.session['end_date'] = str(self.end_date or '')
            self.request.session.modified = True

            if hasattr(self.parent, 'start_date'):
                self.parent.start_date = str(self.start_date or '')
                self.parent.end_date = str(self.end_date or '')
                self.parent.page = 1
                self.parent.load_from_session()

            self.error_message = ""

        except Exception as e:
            logger.error(f"Error applying filter: {str(e)}")
            self.error_message = str(e)

    def clear_date_filter(self):
        try:
            logger.info("Received clear_date_filter")
            self.start_date = ""
            self.end_date = ""
            self.error_message = ""

            if hasattr(self.parent, 'start_date'):
                self.parent.start_date = ""
                self.parent.end_date = ""
                self.parent.page = 1
                self.parent.load_from_session()

            self.request.session['start_date'] = ""
            self.request.session['end_date'] = ""
            self.request.session.modified = True
            logger.info("Cleared session: start_date='', end_date=''")

        except Exception as e:
            logger.error(f"Error clearing filter: {str(e)}")
            self.error_message = str(e)