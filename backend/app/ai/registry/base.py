"""Abstract model registry boundary."""
from abc import ABC, abstractmethod

from ..domain import FeatureVector, ModelOutput


class ModelRegistry(ABC):
    """Resolve a versioned model by name without coupling domain to an engine."""

    @abstractmethod
    def predict(
        self, model_name: str, version: str, features: FeatureVector
    ) -> ModelOutput:
        """Return a validated model output; implementations own model details."""
        raise NotImplementedError
