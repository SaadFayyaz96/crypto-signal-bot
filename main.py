# --- CONFIG ---
import os
import requests
import pandas as pd
import ta
import time

# MEXC API URL for candlestick data
MEXC_API_URL = "https://api.mexc.com/api/v3/klines"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
# Function to send trade signals to Discord
def send_discord_alert(message):
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    
    if response.status_code == 204:
        print("✅ Alert sent to Discord!")
    else:
        print(f"❌ Failed to send alert: {response.status_code}, Response: {response.text}")

# Function to fetch available trading pairs
def get_trading_pairs():
    url = "https://api.mexc.com/api/v3/exchangeInfo"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        trading_pairs = [symbol['symbol'] for symbol in data['symbols'] if symbol['status'] == 'TRADING']
        return trading_pairs
    else:
        print(f"❌ Error fetching trading pairs: {response.status_code}")
        return []

# Function to get technical data (candles) from MEXC API
def get_technical_data(symbol, interval='15m'):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 100  # Fetch last 100 candles
    }
    response = requests.get(MEXC_API_URL, params=params)
    
    if response.status_code != 200:
        print(f"❌ Error fetching data for {symbol}, status code: {response.status_code}")
        return None

    data = response.json()

    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'ignore'])

    df['close'] = df['close'].astype(float)

    # Calculate Indicators
    df['ema_9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['volume'] = df['volume'].astype(float)

    return df

# Function to check trade signals based on EMA, RSI, Volume, and Volatility
def check_trade_signals(symbol):
    df = get_technical_data(symbol)
    
    if df is None:
        print(f"❌ No data for {symbol}")
        return None

    print(f"Checking {symbol}...")

    # Additional conditions for volume, volatility, and trend confirmation
    volume_condition = df['volume'].iloc[-1] > df['volume'].iloc[-2]  # Volume increase
    volatility_condition = abs(df['close'].iloc[-1] - df['close'].iloc[-2]) > 0.01 * df['close'].iloc[-2]  # Price volatility
    trend_condition = df['ema_9'].iloc[-1] > df['ema_21'].iloc[-1]  # EMA trend confirmation

    # Long signal: EMA cross, RSI > 30, volume and volatility conditions met
    if trend_condition and df['rsi'].iloc[-1] > 30 and volume_condition and volatility_condition:
        message = f"🚀 Long Signal on {symbol}"
        print(f"Signal detected: {message}")
        send_discord_alert(message)
        return message

    # Short signal: EMA cross, RSI < 70, volume and volatility conditions met
    elif not trend_condition and df['rsi'].iloc[-1] < 70 and volume_condition and volatility_condition:
        message = f"🔻 Short Signal on {symbol}"
        print(f"Signal detected: {message}")
        send_discord_alert(message)
        return message

    return None

# Fetch trading pairs from MEXC API
symbols = get_trading_pairs()

if not symbols:
    print("❌ No trading pairs available.")
else:
    # Run the bot for each trading pair
    for symbol in symbols:
        signal = check_trade_signals(symbol)
        if signal:
            print(f"✅ Signal detected for {symbol}")
        else:
            print(f"⏳ No trade setup for {symbol}")
        
        # Sleep for a short duration before checking the next symbol
        time.sleep(10)  # Adjust this delay as needed
