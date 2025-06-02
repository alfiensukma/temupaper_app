from datetime import datetime
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
            "is_seed": is_seed
        }

        if record["date"]:
            try:
                date_str = record["date"].split()[0]
                if '/' in date_str:
                    month, day, year = map(int, date_str.split('/'))
                    dt = datetime(year, month, day)
                elif '-' in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    paper_data["date"] = date_str
                    return paper_data
                paper_data["date"] = dt.strftime("%d %B %Y")
            except Exception as e:
                logger.error(f"Error formatting date '{record['date']}': {str(e)}")
                paper_data["date"] = record["date"]
        elif record["year"]:
            paper_data["date"] = str(record["year"])
        else:
            paper_data["date"] = "Unknown date"
        return paper_data

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
            logger.info(f"No filter applied: start_date={start_date}, end_date={end_date}")
            return papers
        try:
            start_year, end_year = int(start_date), int(end_date)
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
        except Exception as e:
            logger.error(f"Error filtering papers by year: {str(e)}")
            return papers