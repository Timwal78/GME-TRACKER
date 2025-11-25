#!/usr/bin/env python3
"""
GME ULTIMATE CYCLE & WARRANT TRACKER
Tracks all cycles + 59M warrants + price levels
"""

import json
import time
import os
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError

# ==========================================
# CONFIGURATION
# ==========================================

WEBHOOK_URL = "https://discord.com/api/webhooks/1432825526564683886/PHhN0YPIc45_lMhUHP0bAf9lIPPLi6IQpQYD9hYTwNRJNznhcNqbmTjCJkm483RVeKd_"
ALERT_DAYS_BEFORE = 7
CHECK_INTERVAL_MINUTES = 60

# GME Warrant Info
WARRANT_STRIKE = 32.00
WARRANT_EXPIRATION = datetime(2026, 10, 30)
TOTAL_WARRANTS = 59_000_000

# Price Alert Levels
PRICE_ALERTS = {
    25.00: "🟡 $25 - Warrants getting attention ($7 from ITM)",
    28.00: "🟠 $28 - Warrants nearly ITM ($4 away) - WATCH CLOSELY",
    30.00: "🔴 $30 - CRITICAL - Dealer hedging begins ($2 from ITM)",
    32.00: "🚨 $32 - WARRANTS IN THE MONEY - EXPLOSION IMMINENT",
    35.00: "💥 $35 - Warrants $3 ITM - MOASS TERRITORY"
}

MOASS_ORIGIN = datetime(2021, 1, 28)

# ==========================================
# CYCLE DEFINITIONS
# ==========================================

CYCLES = {
    # REGULATORY - NEVER COMPRESS
    'ftd35': {
        'name': 'T+35 FTD Settlement',
        'description': 'Reg SHO Rule 204 - ALWAYS 35 days',
        'length': 35,
        'base_date': datetime(2025, 9, 17),
        'type': 'regulatory',
        'emoji': '🔒',
        'alert_days': 7
    },
    
    # MAJOR CYCLES  
    'cycle147': {
        'name': '147-Day Futures Cycle',
        'description': 'Major institutional rollover',
        'length': 147,
        'base_date': MOASS_ORIGIN,
        'type': 'institutional',
        'emoji': '🏛️',
        'alert_days': 14
    },
    
    # FRACTAL COMPRESSION (7-4-1)
    'frac100': {
        'name': '100-Day Base Pattern',
        'length': 100,
        'base_date': MOASS_ORIGIN,
        'type': 'fractal',
        'emoji': '🔢',
        'alert_days': 10
    },
    'frac64': {
        'name': '64-Day Fractal (100×0.64)',
        'length': 64,
        'base_date': datetime(2025, 9, 17),
        'type': 'fractal',
        'emoji': '🔢',
        'alert_days': 7
    },
    'frac41': {
        'name': '41-Day Fractal (64×0.64)',
        'length': 41,
        'base_date': datetime(2025, 10, 23),
        'type': 'fractal',
        'emoji': '🔢',
        'alert_days': 5
    },
    'frac26': {
        'name': '26-Day Fractal (41×0.64)',
        'length': 26,
        'base_date': datetime(2025, 12, 3),
        'type': 'fractal',
        'emoji': '🔢',
        'alert_days': 3
    },
    'frac17': {
        'name': '17-Day Fractal (26×0.64)',
        'length': 17,
        'base_date': datetime(2025, 12, 29),
        'type': 'fractal',
        'emoji': '🔢',
        'alert_days': 2
    },
    'frac11': {
        'name': '11-Day Fractal (17×0.64)',
        'length': 11,
        'base_date': datetime(2026, 1, 15),
        'type': 'fractal',
        'emoji': '🔢',
        'alert_days': 2
    },
    'frac7': {
        'name': '7-Day Fractal (Final)',
        'length': 7,
        'base_date': datetime(2026, 1, 26),
        'type': 'fractal',
        'emoji': '🔢',
        'alert_days': 1
    },
    
    # WARRANT EXPIRATION
    'warrant_exp': {
        'name': 'GME Warrant Expiration',
        'description': '59M warrants @ $32 strike expire',
        'type': 'warrant',
        'emoji': '📜',
        'alert_days': 30
    }
}

# ==========================================
# STORAGE
# ==========================================

STORAGE_FILE = 'gme_ultimate_tracker.json'

def load_storage():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'sent_alerts': {},
        'price_alerts_sent': {},
        'last_known_price': 20.50,
        'stats': {
            'total_alerts': 0,
            'started': str(datetime.now())
        }
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
    if cycle_id == 'warrant_exp':
        return WARRANT_EXPIRATION
    if cycle_id == 'opex':
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
                'name': 'Quarterly OPEX (3rd Friday)',
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
            if 0 <= days_until <= 365:  # Extended for warrant expiration
                cycles.append({
                    'id': cycle_id,
                    'name': cycle_data['name'],
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

def calculate_warrant_status(gme_price):
    """Calculate warrant metrics"""
    intrinsic = max(0, gme_price - WARRANT_STRIKE)
    distance_to_itm = WARRANT_STRIKE - gme_price if gme_price < WARRANT_STRIKE else 0
    percent_to_itm = (distance_to_itm / gme_price * 100) if gme_price > 0 else 0
    
    days_to_exp = (WARRANT_EXPIRATION - datetime.now()).days
    
    # Estimate time value (rough)
    if gme_price < WARRANT_STRIKE:
        time_value = max(0.50, min(5.00, (WARRANT_STRIKE - gme_price) * 0.15))
    else:
        time_value = max(0.20, 2.00 * (days_to_exp / 365))
    
    estimated_warrant_price = intrinsic + time_value
    
    # Hedging estimate
    if gme_price >= WARRANT_STRIKE:
        hedge_ratio = 0.70  # Deep ITM
    elif gme_price >= 30:
        hedge_ratio = 0.40  # Near ITM
    elif gme_price >= 28:
        hedge_ratio = 0.20  # Getting close
    else:
        hedge_ratio = 0.05  # Far OTM
    
    shares_to_hedge = int(TOTAL_WARRANTS * hedge_ratio)
    
    return {
        'intrinsic': intrinsic,
        'distance_to_itm': distance_to_itm,
        'percent_to_itm': percent_to_itm,
        'estimated_warrant_price': estimated_warrant_price,
        'hedge_ratio': hedge_ratio,
        'shares_to_hedge': shares_to_hedge,
        'days_to_expiration': days_to_exp
    }

def get_next_price_alert(current_price, sent_alerts):
    """Find next unalerted price level"""
    for price_level in sorted(PRICE_ALERTS.keys()):
        alert_key = f"price_{price_level}"
        if current_price >= price_level and alert_key not in sent_alerts:
            return price_level, PRICE_ALERTS[price_level]
    return None, None

# ==========================================
# DISCORD ALERTS
# ==========================================

def send_discord_message(embed):
    """Send embed to Discord"""
    payload = {'username': 'GME Ultimate Tracker', 'embeds': [embed]}
    
    try:
        req = Request(WEBHOOK_URL)
        req.add_header('Content-Type', 'application/json')
        data = json.dumps(payload).encode('utf-8')
        
        with urlopen(req, data) as response:
            return response.status == 204
    except:
        return False

def send_cycle_alert(cycle):
    """Alert for upcoming cycle"""
    days = cycle['days_until']
    
    if days <= 3:
        urgency = '🚨 CRITICAL ALERT'
        color = 16711680
    elif days <= 7:
        urgency = '⚠️ WARNING'
        color = 16776960
    else:
        urgency = '📅 UPCOMING'
        color = 65280
    
    embed = {
        'title': f"{urgency}: {cycle['name']}",
        'description': f"**{days} day{'s' if days != 1 else ''} until cycle completion**",
        'color': color,
        'fields': [
            {'name': '📅 Date', 'value': cycle['date'].strftime('%A, %B %d, %Y'), 'inline': False},
            {'name': '⏰ Days Until', 'value': f"{days} day{'s' if days != 1 else ''}", 'inline': True},
            {'name': '🔄 Type', 'value': cycle['type'].title(), 'inline': True}
        ],
        'footer': {'text': 'GME Ultimate Tracker'},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return send_discord_message(embed)

def send_price_alert(price_level, description, current_price, warrant_info):
    """Alert for price level breach"""
    embed = {
        'title': f"🎯 PRICE ALERT: GME ${price_level:.2f}",
        'description': description,
        'color': 16776960 if price_level < 32 else 16711680,
        'fields': [
            {'name': '💰 Current GME Price', 'value': f"${current_price:.2f}", 'inline': True},
            {'name': '🎯 Alert Level', 'value': f"${price_level:.2f}", 'inline': True},
            {'name': '📜 Warrant Strike', 'value': f"${WARRANT_STRIKE:.2f}", 'inline': True},
            {'name': '📊 Distance to ITM', 'value': f"${warrant_info['distance_to_itm']:.2f} ({warrant_info['percent_to_itm']:.1f}%)", 'inline': True},
            {'name': '💎 Est. Warrant Value', 'value': f"${warrant_info['estimated_warrant_price']:.2f}", 'inline': True},
            {'name': '🔄 Hedge Ratio', 'value': f"{warrant_info['hedge_ratio']*100:.0f}%", 'inline': True},
            {'name': '📈 Shares to Hedge', 'value': f"{warrant_info['shares_to_hedge']:,}", 'inline': False}
        ],
        'footer': {'text': f"59M warrants • {warrant_info['days_to_expiration']} days to expiration"},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return send_discord_message(embed)

def send_warrant_summary(gme_price, warrant_info):
    """Send daily warrant status summary"""
    if gme_price >= WARRANT_STRIKE:
        status = "🚨 IN THE MONEY"
        color = 16711680
    elif gme_price >= 30:
        status = "🔴 CRITICAL ZONE"
        color = 16744192
    elif gme_price >= 28:
        status = "🟠 APPROACHING"
        color = 16776960
    else:
        status = "🟡 MONITORING"
        color = 65280
    
    embed = {
        'title': f"📜 GME WARRANT STATUS - {status}",
        'description': f"Daily warrant & price update for {datetime.now().strftime('%B %d, %Y')}",
        'color': color,
        'fields': [
            {'name': '💰 GME Price', 'value': f"${gme_price:.2f}", 'inline': True},
            {'name': '🎯 Strike Price', 'value': f"${WARRANT_STRIKE:.2f}", 'inline': True},
            {'name': '📏 Distance', 'value': f"${warrant_info['distance_to_itm']:.2f} ({warrant_info['percent_to_itm']:.1f}%)", 'inline': True},
            {'name': '💎 Warrant Value (Est)', 'value': f"${warrant_info['estimated_warrant_price']:.2f}", 'inline': True},
            {'name': '🔄 Hedge Ratio', 'value': f"{warrant_info['hedge_ratio']*100:.0f}%", 'inline': True},
            {'name': '📈 Shares Hedged', 'value': f"{warrant_info['shares_to_hedge']:,}", 'inline': True},
            {'name': '⏰ Days to Expiration', 'value': f"{warrant_info['days_to_expiration']} days", 'inline': False}
        ],
        'footer': {'text': f"Total: {TOTAL_WARRANTS:,} warrants outstanding"},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return send_discord_message(embed)

def send_test_alert():
    """Test alert"""
    embed = {
        'title': '✅ GME Ultimate Tracker - System Online',
        'description': 'Tracking cycles + 59M warrants @ $32 strike',
        'color': 65280,
        'fields': [
            {'name': 'Status', 'value': '🟢 Connected', 'inline': True},
            {'name': 'Started', 'value': datetime.now().strftime('%I:%M %p'), 'inline': True},
            {'name': 'Features', 'value': '• All FTD/Fractal Cycles\n• Quarterly OPEX\n• Warrant Tracking\n• Price Level Alerts', 'inline': False}
        ]
    }
    
    return send_discord_message(embed)

# ==========================================
# MAIN LOGIC
# ==========================================

def check_and_alert():
    """Main check routine"""
    storage = load_storage()
    upcoming = get_all_upcoming_cycles()
    
    gme_price = storage.get('last_known_price', 20.50)
    warrant_info = calculate_warrant_status(gme_price)
    
    alerts_sent = 0
    
    # Check cycle alerts
    for cycle in upcoming:
        if cycle['days_until'] <= cycle['alert_days']:
            alert_key = f"{cycle['id']}_{cycle['date'].strftime('%Y-%m-%d')}"
            
            if alert_key not in storage['sent_alerts']:
                print(f"🔔 Cycle alert: {cycle['name']} ({cycle['days_until']}d)")
                
                if send_cycle_alert(cycle):
                    storage['sent_alerts'][alert_key] = datetime.now().isoformat()
                    alerts_sent += 1
    
    # Check price level alerts
    price_level, description = get_next_price_alert(gme_price, storage.get('price_alerts_sent', {}))
    if price_level:
        alert_key = f"price_{price_level}"
        print(f"🎯 Price alert: ${price_level} - {description}")
        
        if send_price_alert(price_level, description, gme_price, warrant_info):
            if 'price_alerts_sent' not in storage:
                storage['price_alerts_sent'] = {}
            storage['price_alerts_sent'][alert_key] = datetime.now().isoformat()
            alerts_sent += 1
    
    if alerts_sent > 0:
        storage['stats']['total_alerts'] = storage['stats'].get('total_alerts', 0) + alerts_sent
        save_storage(storage)
    
    return len(upcoming), alerts_sent, warrant_info

def print_status(active, warrant_info):
    """Print status"""
    now = datetime.now()
    next_check = now + timedelta(minutes=CHECK_INTERVAL_MINUTES)
    
    print(f"""
📊 STATUS:
   Active Cycles: {active}
   Last Check: {now.strftime('%I:%M:%S %p')}
   Next Check: {next_check.strftime('%I:%M:%S %p')}

📜 WARRANT STATUS:
   Distance to $32: ${warrant_info['distance_to_itm']:.2f} ({warrant_info['percent_to_itm']:.1f}%)
   Est. Warrant Price: ${warrant_info['estimated_warrant_price']:.2f}
   Hedge Ratio: {warrant_info['hedge_ratio']*100:.0f}%
   Shares to Hedge: {warrant_info['shares_to_hedge']:,}
   Days to Expiration: {warrant_info['days_to_expiration']}
    """)

def main():
    """Main loop"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║       GME ULTIMATE CYCLE & WARRANT TRACKER                   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("🚀 Starting up...\n")
    print("📤 Sending test alert...")
    
    if send_test_alert():
        print("✅ Test alert sent! Check Discord.\n")
    else:
        print("⚠️  Could not send test alert.\n")
    
    print("✅ System running!")
    print("   • Tracking all FTD/Fractal cycles")
    print("   • Monitoring 59M warrants @ $32 strike")
    print("   • Price level alerts at $25, $28, $30, $32, $35")
    print("   (Press Ctrl+C to stop)\n")
    
    check_count = 0
    
    try:
        while True:
            check_count += 1
            now = datetime.now()
            
            print(f"\n{'='*60}")
            print(f"Check #{check_count} - {now.strftime('%A, %B %d - %I:%M:%S %p')}")
            print('='*60)
            
            active, sent, warrant_info = check_and_alert()
            
            if sent > 0:
                print(f"\n✅ Sent {sent} new alert(s)")
            else:
                print(f"\n💤 No new alerts")
            
            print_status(active, warrant_info)
            
            print(f"😴 Sleeping for {CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Tracker stopped")
        storage = load_storage()
        print(f"\n📊 STATS:")
        print(f"   Total alerts: {storage['stats'].get('total_alerts', 0)}")
        print(f"   Running since: {storage['stats'].get('started', 'Unknown')}")
        print("\n👋 LFG!\n")

if __name__ == "__main__":
    main()
