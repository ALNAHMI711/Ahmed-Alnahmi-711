*** Begin Patch
*** Update File: backend/app/execution/exits.py
@@
-def should_trigger(kind: str, mark: Decimal, trigger: Decimal, side: str) -> bool:
-    if kind in {'TP','TRAILING'}: return mark >= trigger if side == 'SELL' else mark <= trigger
-    return mark <= trigger if side == 'SELL' else mark >= trigger
+def should_trigger(kind: str, mark: Decimal, trigger: Decimal, side: str) -> bool:
+    """Return True when a conditional exit should trigger based on market mark.
+
+    We treat any kind starting with 'TP' (e.g. TP1..TP7) as the TP family for
+    trigger direction only. This does NOT implement any TP-specific sizing or
+    sequencing — those business rules are intentionally left BLOCKED until an
+    explicit definition exists in the codebase.
+    """
+    # Treat TP* (e.g., TP1..TP7) as the TP family for trigger direction.
+    is_tp_family = kind == 'TP' or (isinstance(kind, str) and kind.startswith('TP'))
+    if is_tp_family or kind == 'TRAILING':
+        # Take-profit style trigger: SELL triggers when mark >= trigger; BUY triggers when mark <= trigger.
+        return mark >= trigger if side == 'SELL' else mark <= trigger
+    # For SL/PARTIAL_CLOSE/BREAK_EVEN: inverse direction (stop-loss style)
+    return mark <= trigger if side == 'SELL' else mark >= trigger
*** End Patch