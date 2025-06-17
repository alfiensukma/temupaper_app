from django_unicorn.components import UnicornView
from typing import List
import logging

logger = logging.getLogger(__name__)

class YearRangePickerView(UnicornView):
    start_date = ""
    end_date = ""
    years = list(range(2025, 2019, -1))
    error_message = ""
    
    def mount(self):
        if self.parent and hasattr(self.parent, 'start_date') and hasattr(self.parent, 'end_date'):
            self.start_date = self.parent.start_date
            self.end_date = self.parent.end_date

    def updated(self, name, value):
        self.validate_dates()

    def validate_dates(self):
        self.error_message = ""
        if self.start_date and self.end_date:
            try:
                if int(self.start_date) > int(self.end_date):
                    self.error_message = "Tahun awal tidak boleh lebih besar dari tahun akhir."
                    return False
            except (ValueError, TypeError):
                self.error_message = "Format tahun tidak valid."
                return False
        return True

    def clear_date_filter(self):
        self.start_date = ""
        self.end_date = ""
        self.error_message = ""
        if self.parent:
            self.parent.set_dates_and_reload("", "")

    def apply_filter(self):
        if not self.validate_dates():
            return

        if self.parent:
            self.parent.set_dates_and_reload(self.start_date, self.end_date)