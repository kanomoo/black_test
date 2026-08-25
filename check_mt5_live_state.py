import MetaTrader5 as mt5

mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
if not mt5.initialize(path=mt5_path):
    print("MT5 initialize failed:", mt5.last_error())
    quit()

acc_info = mt5.account_info()
print("==========================================================================")
print("  CURRENT METATRADER 5 LIVE ACCOUNT & CHART STATUS  ")
print("==========================================================================")

if acc_info:
    print(f"Account Login   : {acc_info.login}")
    print(f"Broker Server   : {acc_info.server}")
    print(f"Currency & Type : {acc_info.currency} (Balance: {acc_info.balance}, Equity: {acc_info.equity})")
    print(f"Trade Allowed   : {acc_info.trade_allowed}")
    print(f"EA Trade Allowed: {acc_info.trade_expert}")

positions = mt5.positions_get()
print(f"Open Positions  : {len(positions) if positions else 0}")
if positions:
    for p in positions:
        print(f" -> Ticket: {p.ticket} | Symbol: {p.symbol} | Type: {p.type} | Volume: {p.volume} | Profit: {p.profit}")

symbols = ["XAUUSDc", "XAUUSD"]
for s in symbols:
    tick = mt5.symbol_info_tick(s)
    if tick:
        print(f"Symbol {s:<10} : Bid={tick.bid}, Ask={tick.ask}, Time={tick.time}")

mt5.shutdown()
