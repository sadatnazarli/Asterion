import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class MarketProvider(ABC):
    @abstractmethod
    def get_quote(self, ticker: str) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    def get_history(self, ticker: str, range_str: str) -> List[Dict[str, Any]] | None:
        pass
