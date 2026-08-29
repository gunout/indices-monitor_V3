# serv.py - Serveur Flask complet avec patch yfinance
import warnings
warnings.filterwarnings('ignore')

# PATCH YFINANCE - API DIRECTE
import yfinance_patch  # Ceci active le patch

from flask import Flask, render_template, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import os
import pytz
import logging
import time
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = 'trading-monitor-secret-key'
CORS(app)

US_TIMEZONE = pytz.timezone('America/New_York')
cache = {}
CACHE_DURATION = 300  # 5 minutes

# ============================================================
# CATÉGORIES D'INDICES - Avec Asie du Sud-Est & Nord-Est
# ============================================================

CATEGORIES = [
    # === EUROPE ===
    {'id': 'eu-major', 'name': 'Europe Principaux', 'color': '#ffd166', 'icon': 'fa-earth-europe',
     'symbols': ['^FTSE', '^GDAXI', '^FCHI', '^STOXX50E', '^SMI', '^IBEX', '^FTSEMIB']},
    {'id': 'eu-other', 'name': 'Europe Étendue', 'color': '#ef8354', 'icon': 'fa-map-location-dot',
     'symbols': ['^FTMC', '^MDAXI', '^CN20', '^STOXX', '^AEX', '^BFX']},
    
    # === CAC 40 COMPLET ===
    {'id': 'cac40', 'name': 'CAC 40 Complet', 'color': '#1a73e8', 'icon': 'fa-trophy',
     'symbols': [
         'AC.PA', 'AI.PA', 'AIR.PA', 'ALO.PA', 'ATO.PA', 'CS.PA', 'BNP.PA',
         'EN.PA', 'CA.PA', 'ACA.PA', 'BN.PA', 'DSY.PA', 'EDEN.PA', 'ENGI.PA',
         'EL.PA', 'GLE.PA', 'KER.PA', 'LI.PA', 'LR.PA', 'MC.PA', 'OR.PA',
         'MT.PA', 'ORA.PA', 'RNO.PA', 'RMS.PA', 'SAF.PA', 'SAN.PA', 'SGO.PA',
         'SU.PA', 'STLAP.PA', 'TEP.PA', 'TTE.PA', 'URW.PA', 'VIE.PA', 'DG.PA',
         'VIV.PA', 'WLN.PA'
     ]},
    
    # === US ===
    {'id': 'us-major', 'name': 'US Principaux', 'color': '#00e5a0', 'icon': 'fa-flag-usa',
     'symbols': ['^GSPC', '^DJI', '^IXIC', '^NDX']},
    {'id': 'us-mid', 'name': 'US Mid & Small', 'color': '#06d6a0', 'icon': 'fa-layer-group',
     'symbols': ['^RUT', '^MID', '^SML']},
    
    # === ASIE DÉVELOPPÉE (Japon, HK, Singapour, Australie) ===
    {'id': 'asia-dev', 'name': 'Asie Développée', 'color': '#e63946', 'icon': 'fa-torii-gate',
     'symbols': ['^N225', '^HSI', '^STI', '^AXJO']},
    
    # === ASIE DU NORD-EST (Chine, Corée, Taïwan) ===
    {'id': 'asia-ne', 'name': 'Asie du Nord-Est', 'color': '#c77dff', 'icon': 'fa-globe-asia',
     'symbols': ['^SSEC', '^SZSC', '^KS11', '^TWII']},
    
    # === INDE & ASIE DU SUD-EST (NOUVEAU) ===
    {'id': 'asia-south-east', 'name': 'Inde & Asie du Sud-Est', 'color': '#f4a261', 'icon': 'fa-umbrella-beach',
     'symbols': [
         '^BSESN', '^NSEI',   # Inde
         '^KSE',              # Pakistan
         '^DSEX',             # Bangladesh
         '^CSE',              # Sri Lanka
         '^VNI',              # Vietnam
         '^SET',              # Thaïlande
         '^KLSE',             # Malaisie
         '^JKSE',             # Indonésie
         '^PSEI'              # Philippines
     ]},
    
    # === AMÉRIQUES ===
    {'id': 'americas', 'name': 'Ameriques', 'color': '#4cc9f0', 'icon': 'fa-earth-americas',
     'symbols': ['^MXX', '^BVSP', '^MERV']},
    
    # === CANADA ===
    {'id': 'canada', 'name': 'Canada', 'color': '#e63946', 'icon': 'fa-maple-leaf',
     'symbols': [
         '^TSX', '^TSXV',
         'RY.TO', 'TD.TO', 'SHOP.TO',
         'CNR.TO', 'CP.TO', 'ENB.TO', 'BNS.TO', 'BMO.TO'
     ]},
    
    # === TAUX & VOLATILITÉ ===
    {'id': 'rates', 'name': 'Taux Obligataires', 'color': '#f8961e', 'icon': 'fa-landmark',
     'symbols': ['^TNX', '^TYX', '^FVX', '^IRX']},
    {'id': 'vol', 'name': 'Volatilite', 'color': '#f72585', 'icon': 'fa-bolt',
     'symbols': ['^VIX', '^VXN', '^RVX']},
    
    # === DEVISES & MATIÈRES ===
    {'id': 'fx', 'name': 'Devises', 'color': '#7209b7', 'icon': 'fa-coins',
     'symbols': ['DX-Y.NYB', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X']},
    {'id': 'commod', 'name': 'Matières Premieres', 'color': '#3a86ff', 'icon': 'fa-gem',
     'symbols': ['GC=F', 'CL=F', 'SI=F', 'HG=F']},
    
    # === MONDIAL ===
    {'id': 'global', 'name': 'Mondial & Divers', 'color': '#8d99ae', 'icon': 'fa-globe',
     'symbols': ['^DWCPF', '^NYA', '^DJT']}
]

ALL_SYMBOLS = []
for cat in CATEGORIES:
    for sym in cat['symbols']:
        ALL_SYMBOLS.append({'symbol': sym, 'category': cat['id']})

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def get_cached(key):
    if key in cache:
        data, ts = cache[key]
        if (datetime.now() - ts).seconds < CACHE_DURATION:
            return data
    return None

def set_cached(key, data):
    cache[key] = (data, datetime.now())

def get_interval_for_period(period):
    intervals = {
        '1d': '1m',
        '5d': '5m',
        '1mo': '15m',
        '3mo': '1h',
        '6mo': '1d',
        '1y': '1d'
    }
    return intervals.get(period, '1d')

def safe_float(v, default=0.0):
    try:
        if pd.isna(v) or v is None:
            return default
        return float(v)
    except:
        return default

def safe_int(v, default=0):
    try:
        if pd.isna(v) or v is None:
            return default
        return int(v)
    except:
        return default

# ============================================================
# CALCUL DES INDICATEURS TECHNIQUES
# ============================================================

def calculate_rsi(data, period=14):
    if len(data) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(data)):
        diff = data[i] - data[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def calculate_sma(data, period):
    if len(data) < period:
        return None
    return sum(data[-period:]) / period

def calculate_macd(data, fast=12, slow=26, signal=9):
    if len(data) < slow + signal:
        return None, None
    
    def ema(data, period):
        if len(data) < period:
            return None
        k = 2 / (period + 1)
        result = data[0]
        for i in range(1, len(data)):
            result = data[i] * k + result * (1 - k)
        return result
    
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    if ema_fast is None or ema_slow is None:
        return None, None
    
    macd_line = ema_fast - ema_slow
    return macd_line, macd_line * 0.9

def calculate_volatility(data, period=20):
    if len(data) < period + 1:
        return 0
    returns = []
    for i in range(len(data) - period, len(data)):
        if i > 0 and data[i-1] != 0:
            returns.append((data[i] - data[i-1]) / data[i-1])
    if len(returns) < 2:
        return 0
    std = np.std(returns)
    return std * np.sqrt(252) * 100

def calculate_all_indicators(candles):
    if not candles or len(candles) < 20:
        return {}
    
    close = [c['close'] for c in candles]
    current_price = close[-1]
    
    indicators = {
        'current_price': current_price,
        'last_rsi': calculate_rsi(close, 14),
        'last_sma_20': calculate_sma(close, 20),
        'last_sma_50': calculate_sma(close, 50),
        'volatility': calculate_volatility(close),
    }
    
    macd, signal = calculate_macd(close)
    indicators['last_macd'] = macd
    indicators['last_macd_signal'] = signal
    
    # Signaux
    signals = []
    score = 0
    
    if indicators['last_rsi'] is not None:
        if indicators['last_rsi'] < 30:
            signals.append({'type': 'buy', 'indicator': 'RSI', 'value': f"{indicators['last_rsi']:.1f}", 'message': 'Zone de survente'})
            score += 15
        elif indicators['last_rsi'] > 70:
            signals.append({'type': 'sell', 'indicator': 'RSI', 'value': f"{indicators['last_rsi']:.1f}", 'message': 'Zone de surachat'})
            score -= 15
    
    if indicators['last_macd'] is not None and indicators['last_macd_signal'] is not None:
        if indicators['last_macd'] > indicators['last_macd_signal']:
            signals.append({'type': 'buy', 'indicator': 'MACD', 'value': f"{indicators['last_macd']:.3f}", 'message': 'Signal haussier'})
            score += 10
        else:
            signals.append({'type': 'sell', 'indicator': 'MACD', 'value': f"{indicators['last_macd']:.3f}", 'message': 'Signal baissier'})
            score -= 10
    
    if score > 20:
        recommendation = 'ACHAT'
        confidence = min(95, 50 + abs(score) * 0.8)
    elif score < -20:
        recommendation = 'VENTE'
        confidence = min(95, 50 + abs(score) * 0.8)
    else:
        recommendation = 'NEUTRE'
        confidence = 50 + (abs(score) / 2)
    
    indicators['signals'] = signals
    indicators['recommendation'] = recommendation
    indicators['confidence'] = min(95, max(15, confidence))
    indicators['score'] = score
    
    return indicators

# ============================================================
# ROUTES API
# ============================================================

@app.route('/')
def index():
    """Sert la page principale"""
    return send_file('monitor.html')

@app.route('/<path:path>')
def static_files(path):
    """Sert les fichiers statiques"""
    if os.path.exists(path):
        return send_file(path)
    return "File not found", 404

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/categories')
def get_categories():
    """Retourne les catégories"""
    return jsonify(CATEGORIES)

@app.route('/api/chart/<symbol>')
def get_chart(symbol):
    """Récupère les données de chandeliers"""
    try:
        period = request.args.get('period', '1mo')
        interval = get_interval_for_period(period)
        
        cache_key = f"chart_{symbol}_{period}"
        cached = get_cached(cache_key)
        if cached:
            logger.info(f"✅ Cache pour {symbol}")
            return jsonify(cached)
        
        logger.info(f"📊 Chart request: {symbol} period={period}")
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            logger.warning(f"⚠️ Pas de données pour {symbol}")
            return jsonify({'error': f'No data for {symbol}', 'candles': []}), 404
        
        candles = []
        for idx, row in hist.iterrows():
            candles.append({
                'time': int(idx.timestamp()),
                'open': safe_float(row['Open']),
                'high': safe_float(row['High']),
                'low': safe_float(row['Low']),
                'close': safe_float(row['Close']),
                'volume': safe_int(row['Volume'])
            })
        
        result = {'candles': candles}
        set_cached(cache_key, result)
        
        logger.info(f"✅ {len(candles)} bougies pour {symbol}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erreur {symbol}: {e}")
        return jsonify({'error': str(e), 'candles': []}), 500

@app.route('/api/indicators/<symbol>')
def get_indicators(symbol):
    """Récupère les indicateurs techniques"""
    try:
        period = request.args.get('period', '1mo')
        
        cache_key = f"indicators_{symbol}_{period}"
        cached = get_cached(cache_key)
        if cached:
            return jsonify(cached)
        
        response = get_chart(symbol)
        if hasattr(response, 'json'):
            data = response.json
        else:
            data = response
        
        if isinstance(data, dict) and 'candles' in data:
            candles = data['candles']
        else:
            return jsonify({'error': 'No data'}), 404
        
        indicators = calculate_all_indicators(candles)
        indicators['symbol'] = symbol
        
        set_cached(cache_key, indicators)
        return jsonify(indicators)
        
    except Exception as e:
        logger.error(f"❌ Erreur indicateurs {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-status')
def market_status():
    """Statut du marché"""
    now = datetime.now(US_TIMEZONE)
    is_open = now.weekday() < 5 and 9 <= now.hour <= 16
    return jsonify({
        'status': 'open' if is_open else 'closed',
        'label': 'Ouvert' if is_open else 'Fermé',
        'icon': '🟢' if is_open else '🔴',
        'time': now.strftime('%H:%M:%S')
    })

@app.route('/api/clear-cache')
def clear_cache():
    """Vide le cache"""
    cache.clear()
    return jsonify({'status': 'ok'})

# ============================================================
# LANCEMENT
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("📊 TRADING MONITOR - Version Monde (Asie étendue)")
    print("=" * 70)
    print("🌐 http://localhost:5001")
    print("=" * 70)
    print("📈 Catégories disponibles:")
    for cat in CATEGORIES:
        print(f"   {cat['name']}: {len(cat['symbols'])} symboles")
    print("=" * 70)
    print("⏱️  Cache: 5 minutes")
    print("   API: Yahoo Finance avec patch direct")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5001, debug=True)