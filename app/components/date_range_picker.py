from django_unicorn.components import UnicornView
from typing import List
import logging

logger = logging.getLogger(__name__)

class DateRangePickerView(UnicornView):
    start_date = ""
    end_date = ""
    years: List[int] = []
    error_message = ""

    def mount(self):
        self.years = list(range(2025, 2019, -1))
        if self.parent:
            self.start_date = self.parent.start_date
            self.end_date = self.parent.end_date
            logger.info(f"DateRangePickerView mounted with dates: {self.start_date}-{self.end_date}")

    def validate_dates(self):
        try:
            if self.start_date and self.end_date:
                if int(self.start_date) > int(self.end_date):
                    self.error_message = "Tahun awal tidak boleh lebih besar dari tahun akhir."
                    logger.warning(f"Invalid date range: {self.start_date}-{self.end_date}")
                    return False
            
            # Jika valid, pesan error dikosongkan
            self.error_message = ""
            return True
        except (ValueError, TypeError):
            self.error_message = "Format tahun tidak valid"
            return False

    def _update_parent(self):
        if self.validate_dates() and self.parent:
            logger.info(f"Calling parent set_dates_and_reload with: {self.start_date}, {self.end_date}")
            self.parent.set_dates_and_reload(self.start_date, self.end_date)
    
    def updated_start_date(self, value):
        self._update_parent()

    def updated_end_date(self, value):
        self._update_parent()

    def apply_filter(self):
        self._update_parent()

    def clear_date_filter(self):
        self.error_message = ""
        self.start_date = ""
        self.end_date = ""
        
        if self.parent:
            self.parent.set_dates_and_reload("", "")