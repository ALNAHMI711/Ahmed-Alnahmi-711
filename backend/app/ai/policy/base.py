"""Abstract decision-policy boundary."""
from abc import ABC, abstractmethod

from ..domain import Decision, ModelOutput


class DecisionPolicy(ABC):
    """Translate a model output into a domain decision without execution side effects."""

    @abstractmethod
    def decide(self, output: ModelOutput) -> Decision:
        """Return an immutable policy decision."""
        raise NotImplementedError
