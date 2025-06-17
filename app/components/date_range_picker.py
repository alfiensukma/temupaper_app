from django_unicorn.components import UnicornView

class DateRangePickerView(UnicornView):
    start_date: str = ""
    end_date: str = ""

    def mount(self):
        if self.parent:
            self.start_date = self.parent.start_date
            self.end_date = self.parent.end_date

    def apply_date_filter(self, start_date, end_date):
        """Menerima tanggal dari Javascript dan meneruskannya ke parent."""
        self.start_date = start_date
        self.end_date = end_date
        if self.parent:
            self.parent.set_dates_and_reload(start_date, end_date)