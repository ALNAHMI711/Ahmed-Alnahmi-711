"""Comprehensive tests for the AI domain contracts and boundaries."""

from abc import ABC
from decimal import Decimal

import pytest

from app.ai.domain import (
    Decision,
    Feature,
    FeatureVector,
    ModelOutput,
    RiskDecision,
    Signal,
)
from app.ai.policy import DecisionPolicy
from app.ai.registry import ModelRegistry
from pydantic import ValidationError


def vector() -> FeatureVector:
    return FeatureVector(
        features=(
            Feature(name="rsi", value=Decimal("52.125")),
            Feature(name="atr", value=Decimal("1.2500")),
        ),
        as_of_ms=1_757_000_000_000,
    )


def output() -> ModelOutput:
    return ModelOutput(
        signal=Signal.BUY,
        confidence=Decimal("0.875"),
        score=Decimal("1.250"),
        model_name="trend-model",
        model_version="v1",
    )


def test_feature_vector_is_strict_decimal_first_and_immutable() -> None:
    value = vector()
    assert value.features[0].value == Decimal("52.125")
    with pytest.raises(TypeError):
        value.as_of_ms = 1
    with pytest.raises(ValidationError):
        Feature(name="rsi", value=0.5)


def test_feature_vector_rejects_duplicate_names_and_mutable_input() -> None:
    with pytest.raises(ValidationError):
        FeatureVector(
            features=(
                Feature(name="rsi", value=Decimal(1)),
                Feature(name="rsi", value=Decimal(2)),
            ),
            as_of_ms=1,
        )
    with pytest.raises(ValidationError):
        FeatureVector(features=[Feature(name="rsi", value=Decimal(1))], as_of_ms=1)


def test_feature_rejects_non_finite_decimal() -> None:
    for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(ValidationError):
            Feature(name="x", value=value)


def test_model_output_validates_decimal_confidence_and_bounds() -> None:
    result = output()
    assert result.confidence == Decimal("0.875")
    with pytest.raises(ValidationError):
        ModelOutput(
            signal=Signal.BUY,
            confidence=1.1,
            score=Decimal(1),
            model_name="m",
            model_version="v1",
        )
    with pytest.raises(ValidationError):
        ModelOutput(
            signal=Signal.BUY,
            confidence=Decimal("-0.01"),
            score=Decimal(1),
            model_name="m",
            model_version="v1",
        )


def test_decision_and_risk_decision_are_immutable_and_forbid_unknown_fields() -> None:
    decision = Decision(
        signal=Signal.SELL,
        confidence=Decimal("0.75"),
        rationale="trend reversal",
        policy_version="policy-v1",
    )
    risk = RiskDecision(
        approved=True,
        max_notional=Decimal("1000.00"),
        stop_loss_pct=Decimal("0.02"),
        take_profit_pct=Decimal("0.04"),
        rationale="within configured risk budget",
        policy_version="risk-v1",
    )
    assert decision.signal is Signal.SELL
    assert risk.max_notional == Decimal("1000.00")
    with pytest.raises(TypeError):
        risk.approved = False
    with pytest.raises(ValidationError):
        Decision(
            signal=Signal.HOLD,
            confidence=Decimal("0.5"),
            rationale="hold",
            policy_version="v1",
            unexpected="forbidden",
        )


def test_risk_decision_rejects_float_contamination_and_invalid_ranges() -> None:
    with pytest.raises(ValidationError):
        RiskDecision(
            approved=True,
            max_notional=1000.0,
            stop_loss_pct=Decimal("0.02"),
            take_profit_pct=Decimal("0.04"),
            rationale="ok",
            policy_version="v1",
        )
    with pytest.raises(ValidationError):
        RiskDecision(
            approved=True,
            max_notional=Decimal(1),
            stop_loss_pct=Decimal("1.01"),
            take_profit_pct=Decimal("0.04"),
            rationale="bad",
            policy_version="v1",
        )


def test_abstract_registry_and_policy_are_real_boundaries() -> None:
    assert issubclass(ModelRegistry, ABC)
    assert issubclass(DecisionPolicy, ABC)
    with pytest.raises(TypeError):
        ModelRegistry()
    with pytest.raises(TypeError):
        DecisionPolicy()


def test_registry_and_policy_contracts_accept_only_domain_types() -> None:
    class Registry(ModelRegistry):
        def predict(self, model_name: str, version: str, features: FeatureVector) -> ModelOutput:
            assert features is not None
            return output()

    class Policy(DecisionPolicy):
        def decide(self, model_output: ModelOutput) -> Decision:
            return Decision(
                signal=model_output.signal,
                confidence=model_output.confidence,
                rationale="test policy",
                policy_version="v1",
            )

    result = Registry().predict("m", "v1", vector())
    decision = Policy().decide(result)
    assert decision.signal is Signal.BUY
    assert decision.confidence == Decimal("0.875")
