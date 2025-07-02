from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def format_date_to_indonesian(date_str: str, fallback_year: str = "N/A") -> str:
    if not date_str:
        return fallback_year

    try:
        # format YYYY-MM-DD
        if '-' in date_str:
            dt_object = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
        # format M/D/YYYY
        elif '/' in date_str:
            dt_object = datetime.strptime(date_str.split()[0], "%m/%d/%Y")
        # if does not match any known format
        else:
            return fallback_year

        indonesian_months = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni", 
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        
        day = dt_object.day
        month = indonesian_months[dt_object.month]
        year = dt_object.year
        
        return f"{day} {month} {year}"

    except (ValueError, TypeError) as e:
        logger.warning(f"Gagal memformat tanggal '{date_str}': {e}. Menggunakan tahun sebagai fallback.")
        return fallback_year