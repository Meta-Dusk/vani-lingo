from datetime import datetime

def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """Ensures value stays between `min_value` and `max_value`."""
    return max(min_value, min(value, max_value))

def is_vani_bday() -> bool:
    now = datetime.now()
    if now.month == 3 and now.day == 7:
        return True
    return False