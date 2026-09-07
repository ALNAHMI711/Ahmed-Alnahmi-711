from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.database import Base, ApiAccount
from backend.app.execution.models import Position, Trade
from backend.app.risk.snapshot import build_snapshot


def make_db():
    # Import execution models before create_all so their tables are registered.
    import backend.app.execution.models  # noqa: F401

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def make_account(db: Session, account_id: str):
    account = ApiAccount(
        id=account_id,
        name=f"test-{account_id}",
        market="spot",
        encrypted_key="encrypted-key",
        encrypted_secret="encrypted-secret",
        enabled=True,
    )
    db.add(account)
    db.commit()


def test_snapshot_uses_persisted_positions_not_client_values():
    engine = make_db()

    with Session(engine) as db:
        account_id = "account-1"
        make_account(db, account_id)

        db.add(
            Position(
                account_id=account_id,
                market="spot",
                symbol="BTCUSDT",
                quantity=Decimal("2"),
                average_entry_price=Decimal("100"),
                mark_price=Decimal("110"),
                realized_pnl=Decimal("0"),
                unrealized_pnl=Decimal("20"),
                fees=Decimal("1"),
                funding=Decimal("0"),
                state="OPEN",
            )
        )
        db.commit()

        snapshot = build_snapshot(
            db,
            account_id=account_id,
            symbol="BTCUSDT",
            requested_quantity=Decimal("1"),
            mark_price=Decimal("110"),
        )

        assert snapshot.open_positions == 1
        assert snapshot.exposure == 330.0
        assert snapshot.position_size == 110.0
        assert snapshot.daily_loss == 0.0


def test_snapshot_daily_loss_uses_persisted_trade():
    engine = make_db()

    with Session(engine) as db:
        account_id = "account-2"
        make_account(db, account_id)

        db.add(
            Trade(
                account_id=account_id,
                market="spot",
                symbol="BTCUSDT",
                exchange_trade_id="trade-1",
                exchange_order_id="order-1",
                side="SELL",
                quantity=Decimal("1"),
                price=Decimal("90"),
                quote_quantity=Decimal("90"),
                fee=Decimal("1"),
                realized_pnl=Decimal("-10"),
                occurred_at=datetime.utcnow(),
            )
        )
        db.commit()

        snapshot = build_snapshot(
            db,
            account_id=account_id,
            symbol="BTCUSDT",
            requested_quantity=Decimal("1"),
            mark_price=Decimal("100"),
        )

        assert snapshot.daily_loss == 10.0
