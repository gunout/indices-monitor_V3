# yfinance_patch.py - Patch pour l'API Yahoo Finance directe
import yfinance as yf
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import random

def get_yahoo_data_direct(symbol, period='1d', interval='1m'):
    """Récupère les données directement via l'API Yahoo Finance"""
    try:
        period_map = {
            '1d': '1d', '5d': '5d', '1mo': '1mo', 
            '3mo': '3mo', '6mo': '6mo', '1y': '1y'
        }
        
        interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m',
            '1h': '60m', '1d': '1d'
        }
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            'interval': interval_map.get(interval, '1m'),
            'range': period_map.get(period, '1d'),
            'includePrePost': 'false'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://finance.yahoo.com',
            'Referer': 'https://finance.yahoo.com/'
        }
        
        time.sleep(random.uniform(0.3, 0.8))
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"⚠️ API directe échouée pour {symbol}: status {response.status_code}")
            return None
            
        data = response.json()
        
        if 'chart' not in data or 'result' not in data['chart']:
            return None
            
        result = data['chart']['result'][0]
        if result is None:
            return None
            
        timestamps = result.get('timestamp', [])
        quote = result.get('indicators', {}).get('quote', [{}])[0]
        
        if not timestamps or not quote:
            return None
            
        df = pd.DataFrame({
            'Open': quote.get('open', []),
            'High': quote.get('high', []),
            'Low': quote.get('low', []),
            'Close': quote.get('close', []),
            'Volume': quote.get('volume', [])
        })
        
        df.index = pd.to_datetime(timestamps, unit='s')
        df = df.dropna()
        
        if not df.empty:
            print(f"✅ API directe OK pour {symbol} ({len(df)} bougies)")
            return df
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur API directe pour {symbol}: {e}")
        return None

def get_yahoo_data_fallback(symbol, period='1d', interval='1m'):
    """Méthode fallback avec yfinance standard"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if not hist.empty:
            print(f"✅ Fallback yfinance OK pour {symbol}")
            return hist
        return None
    except Exception as e:
        print(f"❌ Fallback échoué pour {symbol}: {e}")
        return None

def patch_yfinance():
    """Applique le patch pour utiliser l'API directe"""
    
    original_history = yf.Ticker.history
    
    def patched_history(self, period='1d', interval='1m', *args, **kwargs):
        symbol = self.ticker
        
        try:
            df = get_yahoo_data_direct(symbol, period, interval)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"⚠️ Erreur API directe pour {symbol}: {e}")
        
        try:
            result = original_history(self, period=period, interval=interval, *args, **kwargs)
            if not result.empty:
                return result
        except Exception as e:
            print(f"⚠️ Erreur fallback pour {symbol}: {e}")
        
        print(f"❌ Aucune donnée pour {symbol}")
        return pd.DataFrame()
    
    yf.Ticker.history = patched_history
    print("✅ Patch yfinance appliqué - API directe activée")
    return True

# Appliquer le patch au chargement
patch_yfinance()