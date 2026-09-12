from signals.parser import parse

S='''WLD/USDT\nFuture\nBuy: 0.3407 / 0.3244\nTP: 0.3475 0.3511 0.3548\nSL: 0.2999'''
def test_signal_with_multi_targets():
 s=parse(S); assert s.symbol=='WLDUSDT' and s.entries==(0.3407,.3244) and len(s.take_profits)==3
def test_rejects_unstructured_signal():
 try: parse('buy now')
 except ValueError: return
 assert False
