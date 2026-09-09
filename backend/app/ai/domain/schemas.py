"""Strict, immutable AI domain schemas."""
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Signal(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Feature(BaseModel):
    """One named model feature; values are always finite Decimal."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=128)
    value: Decimal

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("feature name must not be blank")
        return normalized

    @field_validator("value", mode="before")
    @classmethod
    def require_decimal(cls, value: object) -> Decimal:
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError("feature value must be a finite Decimal")
        return value


class FeatureVector(BaseModel):
    """Immutable feature vector with no float or mutable-container boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    features: tuple[Feature, ...] = Field(min_length=1)
    as_of_ms: int = Field(ge=0)

    @field_validator("features")
    @classmethod
    def unique_feature_names(cls, value: tuple[Feature, ...]) -> tuple[Feature, ...]:
        names = [feature.name for feature in value]
        if len(names) != len(set(names)):
            raise ValueError("feature names must be unique")
        return value


class ModelOutput(BaseModel):
    """Pure model inference result; it cannot place or modify an order."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    signal: Signal
    confidence: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    score: Decimal
    model_name: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=64)

    @field_validator("confidence", "score", mode="before")
    @classmethod
    def require_decimal(cls, value: object) -> Decimal:
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError("model numeric outputs must be finite Decimal values")
        return value


class Decision(BaseModel):
    """Policy decision derived from model output, still outside execution."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    signal: Signal
    confidence: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    rationale: str = Field(min_length=1, max_length=512)
    policy_version: str = Field(min_length=1, max_length=64)

    @field_validator("confidence", mode="before")
    @classmethod
    def require_decimal(cls, value: object) -> Decimal:
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError("decision confidence must be a finite Decimal")
        return value


class RiskDecision(BaseModel):
    """Risk verdict for a decision; no exchange or execution behavior."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    approved: bool
    max_notional: Decimal = Field(ge=Decimal(0))
    stop_loss_pct: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    take_profit_pct: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    rationale: str = Field(min_length=1, max_length=512)
    policy_version: str = Field(min_length=1, max_length=64)

    @field_validator("max_notional", "stop_loss_pct", "take_profit_pct", mode="before")
    @classmethod
    def require_decimal(cls, value: object) -> Decimal:
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError("risk numeric values must be finite Decimal values")
        return value
