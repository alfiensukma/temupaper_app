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

    def validate_dates(self):
        self.error_message = ""
        try:
            if self.start_date and self.end_date:
                if int(self.start_date) > int(self.end_date):
                    self.error_message = "Tahun awal tidak boleh lebih besar dari tahun akhir."
                    return False
            return True
        except (ValueError, TypeError):
            self.error_message = "Format tahun tidak valid."
            return False

    def apply_filter(self):
        if not self.validate_dates():
            return
        if self.parent:
            self.parent.set_dates_and_reload(self.start_date, self.end_date)

    def clear_date_filter(self):
        self.error_message = ""
        self.start_date = ""
        self.end_date = ""
        if self.parent:
            self.parent.set_dates_and_reload("", "")