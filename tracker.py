#!/usr/bin/env python3
"""
GME/AMC ULTIMATE CYCLE & WARRANT TRACKER
Real-time prices • Both stocks • No hardcoded BS
"""

import json
import time
import os
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError
import re

# ==========================================
# CONFIGURATION
# ==========================================

WEBHOOK_URL = "https://discord.com/api/webhooks/1432825526564683886/PHhN0YPIc45_lMhUHP0bAf9lIPPLi6IQpQYD9hYTwNRJNznhcNqbmTjCJkm483RVeKd_"
ALERT_DAYS_BEFORE = 7
CHECK_INTERVAL_MINUTES = 60

# GME Warrant Info
GME_WARRANT_STRIKE = 32.00
GME_WARRANT_EXPIRATION = datetime(2026, 10, 30)
GME_TOTAL_WARRANTS = 59_000_000

# GME Price Alert Levels
GME_PRICE_ALERTS = {
    25.00: "🟡 $25 - Warrants getting attention ($7 from ITM)",
    28.00: "🟠 $28 - Warrants nearly ITM ($4 away) - WATCH CLOSELY",
    30.00: "🔴 $30 - CRITICAL - Dealer hedging begins ($2 from ITM)",
    32.00: "🚨 $32 - WARRANTS IN THE MONEY - EXPLOSION IMMINENT",
    35.00: "💥 $35 - Warrants $3 ITM - MOASS TERRITORY"
}

# AMC Price Alerts (no warrants, but track key levels)
AMC_PRICE_ALERTS = {
    5.00: "🟡 $5 - Breaking above key support",
    7.00: "🟠 $7 - Major resistance level",
    10.00: "🔴 $10 - CRITICAL - Psychological barrier",
    15.00: "🚨 $15 - SQUEEZE TERRITORY",
    20.00: "💥 $20 - MOASS POTENTIAL"
}

MOASS_ORIGIN = datetime(2021, 1, 28)

# ==========================================
# CYCLE DEFINITIONS
# ==========================================

CYCLES = {
    # REGULATORY - NEVER COMPRESS
    'ftd35_gme': {
        'name': 'GME T+35 FTD Settlement',
        'ticker': 'GME',
        'length': 35,
        'base_date': datetime(2025, 9, 17),
        'type': 'regulatory',
        'emoji': '🔒',
        'alert_days': 7
    },
    'ftd35_amc': {
        'name': 'AMC T+35 FTD Settlement',
        'ticker': 'AMC',
        'length': 35,
        'base_date': datetime(2025, 9, 17),
        'type': 'regulatory',
        'emoji': '🔒',
        'alert_days': 7
    },
    
    # MAJOR CYCLES
    'cycle147_gme': {
        'name': 'GME 147-Day Futures Cycle',
        'ticker': 'GME',
        'length': 147,
        'base_date': MOASS_ORIGIN,
        'type': 'institutional',
        'emoji': '🏛️',
        'alert_days': 14
    },
    'cycle147_amc': {
        'name': 'AMC 147-Day Futures Cycle',
        'ticker': 'AMC',
        'length': 147,
        'base_date': MOASS_ORIGIN,
        'type': 'institutional',
        'emoji': '🏛️',
        'alert_days': 14
    },
    
    # FRACTAL COMPRESSION (7-4-1) - GME
    'frac100_gme': {'name': 'GME 100-Day Fractal', 'ticker': 'GME', 'length': 100, 'base_date': MOASS_ORIGIN, 'type': 'fractal', 'emoji': '🔢', 'alert_days': 10},
    'frac64_gme': {'name': 'GME 64-Day Fractal', 'ticker': 'GME', 'length': 64, 'base_date': datetime(2025, 9, 17), 'type': 'fractal', 'emoji': '🔢', 'alert_days': 7},
    'frac41_gme': {'name': 'GME 41-Day Fractal', 'ticker': 'GME', 'length': 41, 'base_date': datetime(2025, 10, 23), 'type': 'fractal', 'emoji': '🔢', 'alert_days': 5},
    'frac26_gme': {'name': 'GME 26-Day Fractal', 'ticker': 'GME', 'length': 26, 'base_date': datetime(2025, 12, 3), 'type': 'fractal', 'emoji': '🔢', 'alert_days': 3},
    'frac17_gme': {'name': 'GME 17-Day Fractal', 'ticker': 'GME', 'length': 17, 'base_date': datetime(2025, 12, 29), 'type': 'fractal', 'emoji': '🔢', 'alert_days': 2},
    
    # FRACTAL COMPRESSION (7-4-1) - AMC
    'frac100_amc': {'name': 'AMC 100-Day Fractal', 'ticker': 'AMC', 'length': 100, 'base_date': MOASS_ORIGIN, 'type': 'fractal', 'emoji': '🔢', 'alert_days': 10},
    'frac64_amc': {'name': 'AMC 64-Day Fractal', 'ticker': 'AMC', 'length': 64, 'base_date': datetime(2025, 9, 17), 'type': 'fractal', 'emoji': '🔢', 'alert_days': 7},
    'frac41_amc': {'name': 'AMC 41-Day Fractal', 'ticker': 'AMC', 'length': 41, 'base_date': datetime(2025, 10, 23), 'type': 'fractal', 'emoji': '🔢', 'alert_days': 5},
    'frac26_amc': {'name': 'AMC 26-Day Fractal', 'ticker': 'AMC', 'length': 26, 'base_date': datetime(2025, 12, 3), 'type': 'fractal', 'emoji': '🔢', 'alert_days': 3},
    
    # WARRANT EXPIRATION
    'warrant_gme': {'name': 'GME Warrant Expiration', 'ticker': 'GME', 'type': 'warrant', 'emoji': '📜', 'alert_days': 30}
}

# ==========================================
# REAL-TIME PRICE FETCHING
# ==========================================

def fetch_stock_price(ticker):
    """Fetch real-time stock price from Yahoo Finance"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        req = Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return round(float(price), 2)
    except Exception as e:
        print(f"⚠️  Could not fetch {ticker} price: {e}")
        return None

def fetch_both_prices():
    """Fetch GME and AMC prices"""
    gme = fetch_stock_price('GME')
    amc = fetch_stock_price('AMC')
    
    if gme is None or amc is None:
        print("⚠️  Price fetch failed, using last known prices")
        storage = load_storage()
        gme = gme or storage.get('last_gme_price', 20.50)
        amc = amc or storage.get('last_amc_price', 4.50)
    
    return gme, amc

# ==========================================
# STORAGE
# ==========================================

STORAGE_FILE = 'ultimate_tracker_data.json'

def load_storage():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'sent_alerts': {},
        'gme_price_alerts_sent': {},
        'amc_price_alerts_sent': {},
        'last_gme_price': 20.50,
        'last_amc_price': 4.50,
        'stats': {'total_alerts': 0, 'started': str(datetime.now())}
    }

def save_storage(data):
    with open(STORAGE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ==========================================
# CYCLE CALCULATIONS
# ==========================================

def get_third_friday(year, month):
    date = datetime(year, month, 1)
    fridays = 0
    while fridays < 3:
        if date.weekday() == 4:
            fridays += 1
        if fridays < 3:
            date += timedelta(days=1)
    return date

def get_next_opex():
    now = datetime.now()
    opex_months = [3, 6, 9, 12]
    for year_offset in range(3):
        year = now.year + year_offset
        for month in opex_months:
            opex_date = get_third_friday(year, month)
            if opex_date > now:
                return opex_date
    return None

def calculate_next_cycle(cycle_id, cycle_data):
    if cycle_id == 'warrant_gme':
        return GME_WARRANT_EXPIRATION
    if 'opex' in cycle_id:
        return get_next_opex()
    
    now = datetime.now()
    base = cycle_data['base_date']
    length = cycle_data['length']
    
    days_since = (now - base).days
    cycles_passed = days_since // length
    
    next_date = base + timedelta(days=(cycles_passed + 1) * length)
    return next_date

def get_all_upcoming_cycles():
    now = datetime.now()
    cycles = []
    
    # Add OPEX
    opex = get_next_opex()
    if opex:
        days_until = (opex - now).days
        if 0 <= days_until <= 90:
            cycles.append({
                'id': 'opex',
                'name': 'Quarterly OPEX (Both Stocks)',
                'ticker': 'BOTH',
                'date': opex,
                'days_until': days_until,
                'type': 'regulatory',
                'emoji': '📅',
                'alert_days': 10
            })
    
    # Add all other cycles
    for cycle_id, cycle_data in CYCLES.items():
        next_date = calculate_next_cycle(cycle_id, cycle_data)
        if next_date:
            days_until = (next_date - now).days
            if 0 <= days_until <= 365:
                cycles.append({
                    'id': cycle_id,
                    'name': cycle_data['name'],
                    'ticker': cycle_data.get('ticker', 'BOTH'),
                    'date': next_date,
                    'days_until': days_until,
                    'type': cycle_data['type'],
                    'emoji': cycle_data['emoji'],
                    'alert_days': cycle_data.get('alert_days', 7)
                })
    
    return sorted(cycles, key=lambda x: x['days_until'])

# ==========================================
# WARRANT CALCULATIONS
# ==========================================

def calculate_gme_warrant_status(gme_price):
    """Calculate GME warrant metrics"""
    intrinsic = max(0, gme_price - GME_WARRANT_STRIKE)
    distance = GME_WARRANT_STRIKE - gme_price if gme_price < GME_WARRANT_STRIKE else 0
    percent = (distance / gme_price * 100) if gme_price > 0 else 0
    
    days_to_exp = (GME_WARRANT_EXPIRATION - datetime.now()).days
    
    # Hedge ratio based on proximity to strike
    if gme_price >= GME_WARRANT_STRIKE:
        hedge_ratio = 0.70
    elif gme_price >= 30:
        hedge_ratio = 0.40
    elif gme_price >= 28:
        hedge_ratio = 0.20
    else:
        hedge_ratio = 0.05
    
    shares_to_hedge = int(GME_TOTAL_WARRANTS * hedge_ratio)
    
    return {
        'intrinsic': intrinsic,
        'distance': distance,
        'percent': percent,
        'hedge_ratio': hedge_ratio,
        'shares_to_hedge': shares_to_hedge,
        'days_to_exp': days_to_exp
    }

def get_next_price_alert(ticker, current_price, sent_alerts):
    """Find next unalerted price level"""
    alerts = GME_PRICE_ALERTS if ticker == 'GME' else AMC_PRICE_ALERTS
    
    for price_level in sorted(alerts.keys()):
        alert_key = f"{ticker}_price_{price_level}"
        if current_price >= price_level and alert_key not in sent_alerts:
            return price_level, alerts[price_level]
    return None, None

# ==========================================
# DISCORD ALERTS
# ==========================================

def send_discord_message(embed):
    payload = {'username': 'GME/AMC Ultimate Tracker', 'embeds': [embed]}
    try:
        req = Request(WEBHOOK_URL)
        req.add_header('Content-Type', 'application/json')
        data = json.dumps(payload).encode('utf-8')
        with urlopen(req, data, timeout=10) as response:
            return response.status == 204
    except:
        return False

def send_cycle_alert(cycle):
    days = cycle['days_until']
    urgency = '🚨 CRITICAL' if days <= 3 else '⚠️ WARNING' if days <= 7 else '📅 UPCOMING'
    color = 16711680 if days <= 3 else 16776960 if days <= 7 else 65280
    
    embed = {
        'title': f"{urgency}: {cycle['name']}",
        'description': f"**{days} day{'s' if days != 1 else ''} until cycle**",
        'color': color,
        'fields': [
            {'name': '🎯 Ticker', 'value': cycle['ticker'], 'inline': True},
            {'name': '📅 Date', 'value': cycle['date'].strftime('%A, %B %d, %Y'), 'inline': False},
            {'name': '⏰ Days Until', 'value': f"{days} days", 'inline': True},
            {'name': '🔄 Type', 'value': cycle['type'].title(), 'inline': True}
        ],
        'footer': {'text': 'GME/AMC Ultimate Tracker'},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return send_discord_message(embed)

def send_price_alert(ticker, price_level, description, current_price, warrant_info=None):
    embed = {
        'title': f"🎯 {ticker} PRICE ALERT: ${price_level:.2f}",
        'description': description,
        'color': 16776960 if price_level < 32 else 16711680,
        'fields': [
            {'name': f'💰 Current {ticker}', 'value': f"${current_price:.2f}", 'inline': True},
            {'name': '🎯 Alert Level', 'value': f"${price_level:.2f}", 'inline': True}
        ],
        'footer': {'text': f'{ticker} Price Alert'},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if warrant_info and ticker == 'GME':
        embed['fields'].extend([
            {'name': '📜 Warrant Strike', 'value': f"${GME_WARRANT_STRIKE:.2f}", 'inline': True},
            {'name': '📊 Distance to ITM', 'value': f"${warrant_info['distance']:.2f} ({warrant_info['percent']:.1f}%)", 'inline': True},
            {'name': '🔄 Hedge Ratio', 'value': f"{warrant_info['hedge_ratio']*100:.0f}%", 'inline': True},
            {'name': '📈 Shares to Hedge', 'value': f"{warrant_info['shares_to_hedge']:,}", 'inline': True}
        ])
    
    return send_discord_message(embed)

def send_startup_alert(gme_price, amc_price):
    embed = {
        'title': '✅ GME/AMC Ultimate Tracker - ONLINE',
        'description': 'Real-time tracking for both meme stocks',
        'color': 65280,
        'fields': [
            {'name': '💰 GME Price', 'value': f"${gme_price:.2f}", 'inline': True},
            {'name': '💰 AMC Price', 'value': f"${amc_price:.2f}", 'inline': True},
            {'name': '📜 GME Warrants', 'value': f"{GME_TOTAL_WARRANTS:,} @ ${GME_WARRANT_STRIKE}", 'inline': False},
            {'name': '✨ Features', 'value': '• Real-time prices\n• All cycles tracked\n• Warrant monitoring\n• Price alerts\n• Both stocks!', 'inline': False}
        ],
        'footer': {'text': 'NO HARDCODED PRICES!'}
    }
    return send_discord_message(embed)

# ==========================================
# MAIN LOGIC
# ==========================================

def check_and_alert():
    storage = load_storage()
    upcoming = get_all_upcoming_cycles()
    
    # Fetch real-time prices
    print("📡 Fetching real-time prices...")
    gme_price, amc_price = fetch_both_prices()
    print(f"   GME: ${gme_price:.2f}")
    print(f"   AMC: ${amc_price:.2f}")
    
    # Update storage
    storage['last_gme_price'] = gme_price
    storage['last_amc_price'] = amc_price
    
    gme_warrant = calculate_gme_warrant_status(gme_price)
    alerts_sent = 0
    
    # Check cycle alerts
    for cycle in upcoming:
        if cycle['days_until'] <= cycle['alert_days']:
            alert_key = f"{cycle['id']}_{cycle['date'].strftime('%Y-%m-%d')}"
            if alert_key not in storage['sent_alerts']:
                print(f"🔔 {cycle['name']} ({cycle['days_until']}d)")
                if send_cycle_alert(cycle):
                    storage['sent_alerts'][alert_key] = datetime.now().isoformat()
                    alerts_sent += 1
    
    # Check GME price alerts
    gme_level, gme_desc = get_next_price_alert('GME', gme_price, storage.get('gme_price_alerts_sent', {}))
    if gme_level:
        print(f"🎯 GME ${gme_level} - {gme_desc}")
        if send_price_alert('GME', gme_level, gme_desc, gme_price, gme_warrant):
            if 'gme_price_alerts_sent' not in storage:
                storage['gme_price_alerts_sent'] = {}
            storage['gme_price_alerts_sent'][f"GME_price_{gme_level}"] = datetime.now().isoformat()
            alerts_sent += 1
    
    # Check AMC price alerts
    amc_level, amc_desc = get_next_price_alert('AMC', amc_price, storage.get('amc_price_alerts_sent', {}))
    if amc_level:
        print(f"🎯 AMC ${amc_level} - {amc_desc}")
        if send_price_alert('AMC', amc_level, amc_desc, amc_price):
            if 'amc_price_alerts_sent' not in storage:
                storage['amc_price_alerts_sent'] = {}
            storage['amc_price_alerts_sent'][f"AMC_price_{amc_level}"] = datetime.now().isoformat()
            alerts_sent += 1
    
    if alerts_sent > 0:
        storage['stats']['total_alerts'] = storage['stats'].get('total_alerts', 0) + alerts_sent
        save_storage(storage)
    
    return len(upcoming), alerts_sent, gme_price, amc_price, gme_warrant

def print_status(active, gme_price, amc_price, gme_warrant):
    now = datetime.now()
    next_check = now + timedelta(minutes=CHECK_INTERVAL_MINUTES)
    
    print(f"""
📊 STATUS:
   Active Cycles: {active}
   Last Check: {now.strftime('%I:%M:%S %p')}
   Next Check: {next_check.strftime('%I:%M:%S %p')}

💰 PRICES (LIVE):
   GME: ${gme_price:.2f}
   AMC: ${amc_price:.2f}

📜 GME WARRANT STATUS:
   Distance to $32: ${gme_warrant['distance']:.2f} ({gme_warrant['percent']:.1f}%)
   Hedge Ratio: {gme_warrant['hedge_ratio']*100:.0f}%
   Shares to Hedge: {gme_warrant['shares_to_hedge']:,}
   Days to Expiration: {gme_warrant['days_to_exp']}
    """)

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║       GME/AMC ULTIMATE TRACKER - REAL-TIME PRICES            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("🚀 Starting up...\n")
    print("📡 Fetching initial prices...")
    
    gme, amc = fetch_both_prices()
    print(f"   GME: ${gme:.2f}")
    print(f"   AMC: ${amc:.2f}\n")
    
    print("📤 Sending startup alert...")
    if send_startup_alert(gme, amc):
        print("✅ Startup alert sent!\n")
    
    print("✅ System running!")
    print("   • Real-time GME/AMC prices")
    print("   • All FTD/Fractal cycles")
    print("   • 59M GME warrants @ $32")
    print("   • Price alerts for both stocks")
    print("   (Press Ctrl+C to stop)\n")
    
    check_count = 0
    
    try:
        while True:
            check_count += 1
            now = datetime.now()
            
            print(f"\n{'='*60}")
            print(f"Check #{check_count} - {now.strftime('%A, %B %d - %I:%M:%S %p')}")
            print('='*60)
            
            active, sent, gme, amc, warrant = check_and_alert()
            
            if sent > 0:
                print(f"\n✅ Sent {sent} alert(s)")
            else:
                print(f"\n💤 No new alerts")
            
            print_status(active, gme, amc, warrant)
            
            print(f"😴 Sleeping for {CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Tracker stopped")
        storage = load_storage()
        print(f"\n📊 FINAL STATS:")
        print(f"   Total alerts: {storage['stats'].get('total_alerts', 0)}")
        print(f"   Last GME: ${storage.get('last_gme_price', 0):.2f}")
        print(f"   Last AMC: ${storage.get('last_amc_price', 0):.2f}")
        print("\n🚀 TO THE MOON!\n")

if __name__ == "__main__":
    main()
