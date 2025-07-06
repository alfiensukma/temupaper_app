from app.utils.parse_indonesian_date import format_date_to_indonesian
import logging

logger = logging.getLogger(__name__)

class PaperProcessor:
    @staticmethod
    def format_paper_data(record, is_seed=False):
        paper_data = {
            "paperId": record["paperId"],
            "title": record["title"] or "Untitled",
            "abstract": record["abstract"] or "",
            "citation_count": record["citation_count"] or 0,
            "similarity": record["similarity_score"],
            "authors": record["authors"],
            "date": record["date"],
            "year": record["year"],
            "is_seed": is_seed,
            "rank": record.get("rank", "Tidak Teridentifikasi")
        }

        raw_date = paper_data.get("date")
        fallback_year = paper_data.get("year", "N/A")
        paper_data["date"] = format_date_to_indonesian(
            date_str=raw_date, 
            fallback_year=fallback_year
        )

        return paper_data
    
    @staticmethod
    def filter_papers_by_quartile(papers, quartile):
        if not quartile or quartile == "Semua Peringkat":
            logger.info("No quartile filter applied, returning all papers")
            return papers

        filtered_papers = []
        for paper in papers:
            paper_rank = paper.get('rank', 'Tidak Teridentifikasi')
            effective_rank = 'Tidak Teridentifikasi' if not paper_rank or paper_rank in ['-', ''] else paper_rank

            if quartile == "Tidak Teridentifikasi":
                if effective_rank == 'Tidak Teridentifikasi':
                    filtered_papers.append(paper)
            elif effective_rank == quartile:
                filtered_papers.append(paper)

        logger.info(f"Filtered {len(papers)} papers to {len(filtered_papers)} for quartile: {quartile}")
        return filtered_papers

    @staticmethod
    def process_search_results(knn_details, similar_results):
        papers, seen_ids = [], set()
        for record in knn_details:
            paper_id = record["paperId"]
            if paper_id not in seen_ids:
                seen_ids.add(paper_id)
                papers.append(PaperProcessor.format_paper_data(record, is_seed=True))
        for record in similar_results:
            paper_id = record["paperId"]
            if paper_id not in seen_ids:
                seen_ids.add(paper_id)
                papers.append(PaperProcessor.format_paper_data(record, is_seed=False))
        papers.sort(key=lambda x: x["similarity"] if x["similarity"] is not None else 0.0, reverse=True)
        return papers

    @staticmethod
    def filter_papers_by_year(papers, start_date, end_date):
        if not start_date or not end_date:
            logger.info(f"No year filter applied: start_date={start_date}, end_date={end_date}")
            return papers
        try:
            start_year, end_year = int(start_date), int(end_date)
            if start_year > end_year:
                logger.warning(f"Invalid year range: start_year={start_year} > end_year={end_year}")
                return papers
            filtered_papers = []
            for paper in papers:
                paper_year = None
                if paper["year"]:
                    try:
                        paper_year = int(paper["year"])
                    except (ValueError, TypeError):
                        pass
                if not paper_year and paper["date"]:
                    date_str = paper["date"]
                    try:
                        for part in date_str.split():
                            if part.isdigit() and len(part) == 4:
                                paper_year = int(part)
                                break
                        if not paper_year and '-' in date_str:
                            paper_year = int(date_str.split('-')[0])
                        if not paper_year and '/' in date_str:
                            parts = date_str.split('/')
                            if len(parts) == 3:
                                paper_year = int(parts[2])
                    except (ValueError, TypeError, IndexError):
                        pass
                if paper_year and start_year <= paper_year <= end_year:
                    filtered_papers.append(paper)
            logger.info(f"Filtered {len(papers)} papers to {len(filtered_papers)} for {start_year}-{end_year}")
            return filtered_papers
        except ValueError as e:
            logger.error(f"Error filtering papers by year: {str(e)}")
            return papers