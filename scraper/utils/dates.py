import re


def normalize_time(time_str):
    """
    Normalize time strings to consistent HH:MM 24-hour format.
    Handles: "8:00", "8:30pm", "20:00:00", "19:00", "8:00pm",
    "8:00 pm doors"
    """
    if not time_str:
        return None

    time_str = time_str.strip().lower()
    match = re.search(r"(\d{1,2}:\d{2})(?::\d{2})?\s*([ap]\.?m\.?)?", time_str)
    if not match:
        return None

    time_str = match.group(1)
    meridiem = (match.group(2) or "").replace(".", "")

    is_pm = meridiem == "pm"
    is_am = meridiem == "am"

    parts = time_str.split(":")
    if len(parts) != 2:
        return None

    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        return None

    if is_pm and hours < 12:
        hours += 12
    elif is_am and hours == 12:
        hours = 0

    return f"{hours:02d}:{minutes:02d}"
