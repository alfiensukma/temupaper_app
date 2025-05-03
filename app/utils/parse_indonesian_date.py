from datetime import datetime
import logging

logger = logging.getLogger(__name__)

INDONESIAN_MONTHS = {
    'Januari': '01', 'Februari': '02', 'Maret': '03', 'April': '04',
    'Mei': '05', 'Juni': '06', 'Juli': '07', 'Agustus': '08',
    'September': '09', 'Oktober': '10', 'November': '11', 'Desember': '12'
}

def parse_indonesian_date(date_str):
    try:
        parts = date_str.split(' ')
        if len(parts) != 3:
            raise ValueError(f"Invalid date format: {date_str}")
            
        day, month, year = parts

        month_num = INDONESIAN_MONTHS.get(month)
        if not month_num:
            raise ValueError(f"Invalid month: {month}")
            
        formatted_date = f"{year}-{month_num}-{day.zfill(2)}"
        
        return datetime.strptime(formatted_date, "%Y-%m-%d")
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
        raise