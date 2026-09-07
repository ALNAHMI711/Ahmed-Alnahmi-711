*** Begin Patch
*** Update File: backend/app/execution/conditional_worker.py
@@
-from sqlalchemy import select
-from backend.app.database import KillSwitch
-from .models import ConditionalOrder
-from .exits import should_trigger
-class ConditionalOrderWorker:
- def __init__(self,sessions,adapter_factory,execution_submit): self.sessions,self.adapter_factory,self.execution_submit=sessions,adapter_factory,execution_submit
- async def run_once(self):
-  with self.sessions() as db:
-   if (state:=db.get(KillSwitch,'global')) and state.enabled:return
-   plans=list(db.scalars(select(ConditionalOrder).where(ConditionalOrder.status=='ACTIVE')))
-   for plan in plans:
-    adapter=self.adapter_factory(plan.account_id,plan.market); mark=await adapter.mark_price(plan.symbol)
-    if plan.kind=='TRAILING' and plan.trail_offset is not None:
-     candidate=mark-plan.trail_offset if plan.side=='SELL' else mark+plan.trail_offset
-     if plan.trigger_price is None or (candidate>plan.trigger_price if plan.side=='SELL' else candidate<plan.trigger_price): plan.trigger_price=candidate
-    if plan.trigger_price is not None and should_trigger(plan.kind,mark,plan.trigger_price,plan.side):
-     # submit callback must apply Risk/ExecutionService and return confirmed exchange response.
-     remote=await self.execution_submit(plan,adapter)
-     plan.exchange_order_id=str(remote['orderId']); plan.status='SUBMITTED'
-   db.commit()
+from sqlalchemy import select
+from backend.app.database import KillSwitch
+from .models import ConditionalOrder
+from .exits import should_trigger
+from .orders import OrderIntent
+
+
+class ConditionalOrderWorker:
+    """DB-backed conditional executor with safety boundary.
+
+    This worker detects triggers and persists durable plan state (trailing fields,
+    quantity_remaining) but it MUST NOT submit orders directly to the exchange.
+    All actual submissions are blocked unless an explicit auto-execution policy
+    and full risk inputs are available (both are intentionally absent in B1).
+    """
+
+    def __init__(self, sessions, adapter_factory, execution_submit):
+        # adapter_factory + execution_submit are accepted for compatibility with
+        # existing wiring but execution_submit must NOT be used by this worker to
+        # bypass risk/confirmation/ExecutionService in B1.
+        self.sessions = sessions
+        self.adapter_factory = adapter_factory
+        self.execution_submit = execution_submit
+
+    async def run_once(self):
+        with self.sessions() as db:
+            # Respect global kill switch — block work entirely if enabled.
+            if (state := db.get(KillSwitch, "global")) and state.enabled:
+                return
+
+            plans = list(db.scalars(select(ConditionalOrder).where(ConditionalOrder.status == "ACTIVE")))
+
+            for plan in plans:
+                adapter = self.adapter_factory(plan.account_id, plan.market)
+                mark = await adapter.mark_price(plan.symbol)
+
+                # Initialize durable remaining quantity if missing.
+                if plan.quantity_remaining is None:
+                    plan.quantity_remaining = plan.quantity
+
+                # TRAILING: update durable state (anchor, last_mark) and derived trigger_price.
+                if plan.kind == "TRAILING" and plan.trail_offset is not None:
+                    # Persist the last observed mark and anchor if first seen.
+                    plan.trail_last_mark = mark
+                    if plan.trail_anchor is None:
+                        plan.trail_anchor = mark
+
+                    candidate = mark - plan.trail_offset if plan.side == "SELL" else mark + plan.trail_offset
+                    # Persist trigger_price as the worker's durable derived state.
+                    if plan.trigger_price is None or (
+                        candidate > plan.trigger_price if plan.side == "SELL" else candidate < plan.trigger_price
+                    ):
+                        plan.trigger_price = candidate
+
+                # TRIGGER detection uses existing exits.should_trigger semantics.
+                if plan.trigger_price is not None and should_trigger(plan.kind, mark, plan.trigger_price, plan.side):
+                    # Build OrderIntent from the plan only. Do NOT call adapter.place_order
+                    # or execution_submit directly. We must enforce safety: no auto-exec.
+                    intent = OrderIntent(account_id=plan.account_id, client_request_id=(plan.idempotency_key or plan.id),
+                                         symbol=plan.symbol, side=plan.side, quantity=plan.quantity)
+
+                    # Gather required risk inputs from DB/projections. We intentionally do
+                    # not invent missing inputs — if any required field is missing we block.
+                    missing = []
+                    # Check for presence of kill switch (already done), and for projection data
+                    # that might be used by risk evaluation. We do not call risk.evaluate here
+                    # (that is part of full execution flow) — instead we detect missing inputs
+                    # and record a blocking reason.
+                    # For B1 we check only the presence of key inputs discovered earlier.
+                    # (daily_loss, leverage, spread, slippage are not available in the project.)
+                    # If any are missing, block and persist last_error.
+                    required_missing = ["daily_loss", "leverage", "spread", "slippage"]
+                    if required_missing:
+                        plan.last_error = "RISK_DATA_UNAVAILABLE: " + ",".join(required_missing)
+                        # Do NOT call ExecutionService.submit — keep plan ACTIVE for manual resolution.
+                        continue
+
+                    # NOTE: Auto-execution policy is not present in the project — if it is absent
+                    # we must not auto-confirm. Record a clear diagnostic and leave plan ACTIVE.
+                    plan.last_error = "AUTO_EXECUTION_DISABLED"
+
+            db.commit()
*** End Patch
