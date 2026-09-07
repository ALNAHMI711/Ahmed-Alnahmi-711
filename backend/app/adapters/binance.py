*** Begin Patch
*** Update File: backend/app/adapters/binance.py
@@
-        payload = response.json(); return _d(payload.get("markPrice", payload["price"]))
+        payload = response.json()
+        # Safe fallback: prefer markPrice when present, otherwise use price if available.
+        price_val = payload.get("markPrice") if payload.get("markPrice") is not None else payload.get("price")
+        if price_val is None:
+            raise RuntimeError("unexpected mark/price payload from exchange")
+        return _d(price_val)
*** End Patch