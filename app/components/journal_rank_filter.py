from django_unicorn.components import UnicornView
import logging

logger = logging.getLogger(__name__)

class JournalRankFilterView(UnicornView):
    selected_rank: str = "Semua Peringkat"
    ranks = ["Q1", "Q2", "Q3", "Q4", "Tidak Teridentifikasi"]

    def mount(self):
        if self.parent and hasattr(self.parent, 'journal_rank'):
            self.selected_rank = self.parent.journal_rank
            logger.info(f"Mounted JournalRankFilterView with selected_rank: {self.selected_rank}")

    def set_rank(self, rank):
        logger.info(f"Setting rank to: {rank}")
        self.selected_rank = rank
        if self.parent:
            self.parent.set_journal_rank(rank)
            logger.info(f"Called parent.set_journal_rank with: {rank}")

    def clear_filter(self):
        logger.info("Clearing rank filter")
        self.selected_rank = "Semua Peringkat"
        if self.parent:
            self.parent.set_journal_rank("Semua Peringkat")
            logger.info("Called parent.set_journal_rank with: Semua Peringkat")

    def updated_selected_rank(self, value):
        logger.info(f"Updated selected_rank to: {value}")
        self.selected_rank = value
        if self.parent:
            self.parent.set_journal_rank(value)