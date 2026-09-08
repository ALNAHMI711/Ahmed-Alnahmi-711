"""Walk-forward validation; metrics are historical, never a profitability claim."""
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class FoldResult:
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    train_return: float
    oos_return: float
    passed: bool


@dataclass(frozen=True)
class WalkForwardResult:
    folds: tuple[FoldResult, ...]
    mean_oos_return: float
    pass_rate: float
    robust: bool


def walk_forward(returns: list[float], *, train_size: int, test_size: int, minimum_oos_return: float = 0) -> WalkForwardResult:
    if train_size < 2 or test_size < 1:
        raise ValueError("أحجام النوافذ غير صالحة")
    folds = []
    for start in range(0, len(returns) - train_size - test_size + 1, test_size):
        train = returns[start : start + train_size]
        test = returns[start + train_size : start + train_size + test_size]
        train_return = sum(train)
        oos_return = sum(test)
        folds.append(FoldResult(start, start + train_size, start + train_size, start + train_size + test_size, train_return, oos_return, oos_return >= minimum_oos_return))
    if not folds:
        raise ValueError("البيانات لا تكفي لاختبار Walk-Forward")
    return WalkForwardResult(tuple(folds), mean(f.oos_return for f in folds), mean(f.passed for f in folds), mean(f.passed for f in folds) >= 0.7)
