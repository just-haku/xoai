import time
from collections import deque
from typing import Dict

class RateLimiter:
    """Simple in-memory rate limiter using a sliding window of timestamps."""
    
    def __init__(self):
        # user_id -> deque of timestamps
        self._usage: Dict[str, deque] = {}

    def check(self, user_id: str, limit: int = 15, period: int = 60) -> bool:
        """
        Returns True if the user is within the limit, False otherwise.
        Default: 15 requests per 60 seconds.
        """
        now = time.time()
        
        if user_id not in self._usage:
            self._usage[user_id] = deque()
            
        window = self._usage[user_id]
        
        # Remove expired timestamps
        while window and window[0] < now - period:
            window.popleft()
            
        if len(window) < limit:
            window.append(now)
            return True
        
        return False

# Global instance
a0_limiter = RateLimiter()
