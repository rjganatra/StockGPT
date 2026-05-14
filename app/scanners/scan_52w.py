
import yfinance as yf
import pandas as pd
import ta
from pathlib import Path
from datetime import datetime

universe = pd.read_csv('data/universe/universe.csv')

results = []

for symbol in universe['symbol']:

    try:

        ticker = yf.Ticker(symbol + '.NS')

        hist = ticker.history(period='1y')

        if hist.empty:
            continue

        current_price = hist['Close'].iloc[-1]

        low_52 = hist['Low'].min()

        high_52 = hist['High'].max()

        distance_pct = ((current_price - low_52) / low_52) * 100

        hist['rsi'] = ta.momentum.RSIIndicator(
            hist['Close']
        ).rsi()

        rsi = hist['rsi'].iloc[-1]

        sma50 = hist['Close'].rolling(50).mean().iloc[-1]

        trend = 'Bullish'

        if current_price < sma50:
            trend = 'Bearish'

        score = 0

        if distance_pct < 20:
            score += 25

        if rsi < 45:
            score += 25

        if trend == 'Bullish':
            score += 25

        results.append({
            'symbol': symbol,
            'sector': 'Others',
            'current_price': round(current_price, 2),
            '52w_low': round(low_52, 2),
            '52w_high': round(high_52, 2),
            'distance_pct': round(distance_pct, 2),
            'rsi': round(rsi, 2),
            'trend': trend,
            'score': score
        })

    except Exception as e:

        print(symbol, e)

df = pd.DataFrame(results)

df = df.sort_values(
    'score',
    ascending=False
)

Path('data/scans').mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    'data/scans/latest_scan.csv',
    index=False
)

today = datetime.now().strftime('%Y-%m-%d')

history_path = Path(
    f'data/history/{today}'
)

history_path.mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    history_path / 'latest_scan.csv',
    index=False
)

print('SCAN COMPLETE')
