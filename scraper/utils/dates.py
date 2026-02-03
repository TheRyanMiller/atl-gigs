
def normalize_time(time_str):
    """
    Normalize time strings to consistent HH:MM 24-hour format.
    Handles: "8:00", "8:30pm", "20:00:00", "19:00", "8:00pm"
    """
    if not time_str:
        return None

    time_str = time_str.strip().lower()

    if time_str.count(":") == 2:
        time_str = ":".join(time_str.split(":")[:2])

    is_pm = "pm" in time_str
    is_am = "am" in time_str
    time_str = time_str.replace("pm", "").replace("am", "").strip()

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
