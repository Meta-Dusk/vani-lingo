import socket
from typing import Optional

def is_connected(timeout: Optional[float] = 3):
    try:
        # Try to connect to a reliable host (Google DNS)
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except Exception:
        return False