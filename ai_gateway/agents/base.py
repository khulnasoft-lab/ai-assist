from abc import ABC, abstractmethod
from typing import Any, Optional

__all__ = ["BaseAgentRegistry"]


class BaseAgentRegistry(ABC):
    @abstractmethod
    def get(self, use_case: str, agent_type: str, **kwargs: Optional[Any]) -> Any:
        pass
