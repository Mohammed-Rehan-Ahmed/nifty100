import re
import logging

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def normalize_year(raw) -> str:
    """Convert any year label to YYYY-MM. Returns PARSE_ERROR on failure."""
    if raw is None:
        return "PARSE_ERROR"
    s = str(raw).strip()

    # Already clean: 2023-03
    if re.match(r"^\d{4}-\d{2}$", s):
        return s

    # "Mar 2014" / "Dec 2012"
    m = re.match(r"^([A-Za-z]{3})\s+(\d{4})$", s)
    if m:
        mon = MONTH_MAP.get(m.group(1).lower())
        if mon:
            return f"{m.group(2)}-{mon}"

    # "Mar-23" / "Mar-2023"
    m = re.match(r"^([A-Za-z]{3})-(\d{2,4})$", s)
    if m:
        mon = MONTH_MAP.get(m.group(1).lower())
        yr = m.group(2)
        yr = f"20{yr}" if len(yr) == 2 else yr
        if mon:
            return f"{yr}-{mon}"

    # "FY23" / "FY2023"
    m = re.match(r"^FY(\d{2,4})$", s, re.IGNORECASE)
    if m:
        yr = m.group(1)
        yr = f"20{yr}" if len(yr) == 2 else yr
        return f"{yr}-03"

    # Plain "2023"
    if re.match(r"^\d{4}$", s):
        return f"{s}-03"

    logger.warning("normalize_year failed: %s", raw)
    return "PARSE_ERROR"


def normalize_ticker(raw) -> str:
    """Strip and uppercase ticker. Returns empty string if invalid."""
    if raw is None:
        return ""
    s = str(raw).strip().upper()
    if not (2 <= len(s) <= 12):
        logger.warning("Ticker out of range: %s", s)
        return ""
    return s