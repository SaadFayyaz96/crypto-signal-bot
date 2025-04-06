import os
import requests
import pandas as pd
import ta
import time

# --- CONFIG ---
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
INTERVAL = "15m"
MEXC_API_URL = "https://api.mexc.com/api/v3/klines"

def get_technical_data(symbol, interval='15m'):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 100
    }
    response = requests.get(MEXC_API_URL, params=params)
    if response.status_code != 200:
        print(f"Error fetching data for {symbol}")
        return None
    data = response.json()

    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'
    ])

    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)

    # Indicators
    df['ema_9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['atr'] = ta.volatility.average_true_range(
        df['high'].astype(float), df['low'].astype(float), df['close'], window=14
    )

    return df

def send_discord_alert(message):
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code in [200, 204]:
        print(f"✅ Alert sent: {message}")
    else:
        print(f"❌ Failed to send alert: {response.status_code}, Response: {response.text}")

def check_trade_signals(symbol):
    df = get_technical_data(symbol, interval=INTERVAL)
    if df is None or df.empty:
        return

    last = df.iloc[-1]

    # Signal logic with volume and trend confirmation
    trend_up = last['ema_9'] > last['ema_21']
    trend_down = last['ema_9'] < last['ema_21']
    strong_volume = last['volume'] > df['volume'].rolling(10).mean().iloc[-1]
    high_volatility = last['atr'] > df['atr'].rolling(10).mean().iloc[-1]

    if trend_up and last['rsi'] > 50 and strong_volume and high_volatility:
        send_discord_alert(f"🚀 Long Signal on {symbol}")

    elif trend_down and last['rsi'] < 50 and strong_volume and high_volatility:
        send_discord_alert(f"🔻 Short Signal on {symbol}")

def main():
    print("📡 Starting Crypto Signal Scanner...")
    while True:
        for symbol in SYMBOLS:
            check_trade_signals(symbol)
        time.sleep(60 * 5)  # run every 5 minutes

if __name__ == "__main__":
    main()