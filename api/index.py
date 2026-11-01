from flask import Flask, request, jsonify, send_from_directory, session, redirect
from functools import wraps
import requests
import asyncio
import random
import threading
import uuid
import os
import hmac
import urllib3
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Render ve Local ortam için dizin ayarları
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from smsapi import SmsBomber
except ImportError:
    SmsBomber = None

app = Flask(__name__)
# Render'da Environment kısmına ZENIX_SECRET eklenmezse oturum tutmaz!
app.secret_key = os.environ.get("ZENIX_SECRET", "cok-gizli-rastgele-bir-anahtar-123")

# ==================== AUTH AYARLARI ====================
AUTH_USERNAME = os.environ.get("ZENIX_USER", "zenix")
AUTH_PASSWORD = os.environ.get("ZENIX_PASS", "Zx9!kLm2#pQr7vBn")

def check_auth(username, password):
    return hmac.compare_digest(username or "", AUTH_USERNAME) and hmac.compare_digest(password or "", AUTH_PASSWORD)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            # EĞER İSTEK API'YE GELİYORSA HTML YÖNLENDİRMESİ YAPMA, JSON HATASI DÖN!
            if request.path.startswith('/api'):
                return jsonify({"error": "Oturum süreniz dolmuş veya giriş yapmamışsınız. Lütfen sayfayı yenileyip tekrar giriş yapın."}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ==================== LOGIN SAYFASI ====================
LOGIN_HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ZENIX Giris</title>
<style>body{background:#030305;color:#e2e8f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.login-box{background:rgba(20,25,35,0.8);border:1px solid #333;border-radius:16px;padding:40px;width:360px;text-align:center}
h1{color:#00f0ff}input{width:100%;padding:14px;margin-bottom:15px;background:#111;border:1px solid #333;border-radius:10px;color:#fff;box-sizing:border-box}
button{width:100%;padding:14px;background:linear-gradient(135deg,#00f0ff,#0077ff);color:#000;border:none;border-radius:10px;font-weight:bold;cursor:pointer}
.error{color:#ff3366;margin-top:15px}</style></head><body>
<form class="login-box" method="POST" action="/login"><h1>ZENIX</h1>
<input type="text" name="username" placeholder="Kullanici adi" required>
<input type="password" name="password" placeholder="Sifre" required>
<button type="submit">Giris Yap</button>
{% if error %}<div class="error">{{ error }}</div>{% endif %}</form></body></html>"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if check_auth(request.form.get('username', ''), request.form.get('password', '')):
            session['logged_in'] = True
            session.permanent = True # Oturumun kalıcı olmasını sağlar
            return redirect('/')
        return LOGIN_HTML.replace('{% if error %}<div class="error">{{ error }}</div>{% endif %}', '<div class="error">Hatali giris</div>')
    return LOGIN_HTML.replace('{% if error %}<div class="error">{{ error }}</div>{% endif %}', '')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==================== API & PROXY ====================
PANELABI = "https://api.panelabi.top"
SOLIDARK = "https://solidarksystems.alwaysdata.net"
WAZELY = "https://wazely.vercel.app/api"
ID_API = "https://prox0959.netlify.app/api/search"

USER_PROXIES = [
    {"ip": "45.38.107.97", "port": "6014", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "64.137.96.74", "port": "6641", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "198.23.243.226", "port": "6361", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "38.154.185.97", "port": "6370", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "84.247.60.125", "port": "6095", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "191.96.254.138", "port": "6185", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "198.46.161.42", "port": "5092", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "64.137.10.153", "port": "5803", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "104.164.49.38", "port": "7693", "user": "bgnozpqj", "pass": "f8uanljtufcb"},
    {"ip": "23.26.71.145", "port": "5628", "user": "bgnozpqj", "pass": "f8uanljtufcb"}
]

SMS_JOBS = {}
SMS_LOCK = threading.Lock()

def clean_data(obj):
    if isinstance(obj, list): return [clean_data(i) for i in obj]
    if isinstance(obj, dict): return {k: clean_data(v) for k, v in obj.items() if k.lower() not in ('author','auth','auth_alt','dev','credit','instagram','ig')}
    if isinstance(obj, str):
        for bad in ["@jessy_php", "jessy", "@wazelybaba", "wazely"]: obj = obj.replace(bad, "")
        return obj.strip()
    return obj

def proxy_request(url, timeout=5):
    shuffled = USER_PROXIES[:]; random.shuffle(shuffled)
    for p in shuffled:
        try:
            proxy_url = f"http://{p['user']}:{p['pass']}@{p['ip']}:{p['port']}"
            r = requests.get(url, proxies={"http": proxy_url, "https": proxy_url}, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200: return r, "Kendi Proxy"
        except Exception: continue
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200: return r, "Doğrudan Bağlantı"
    except Exception: pass
    return None, None

async def _run_turbo_limited(bomber, adet, max_concurrent=10):
    services = bomber.get_services(); sem = asyncio.Semaphore(max_concurrent)
    async def run_one(svc):
        async with sem:
            try: await asyncio.to_thread(svc)
            except Exception: pass
    for _ in range(adet):
        await asyncio.gather(*[run_one(svc) for svc in services])

def _sms_worker(job_id, phone, count, mode):
    try:
        b = SmsBomber(phone)
        if mode == 'turbo':
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            loop.run_until_complete(_run_turbo_limited(b, count)); loop.close()
        else: b.run_normal(count)
        summary = {}
        for n, s in b.results:
            summary.setdefault(n, {"ok": 0, "fail": 0})
            if s: summary[n]["ok"] += 1
            else: summary[n]["fail"] += 1
        ok = sum(1 for _, v in b.results if v); fl = len(b.results) - ok
        with SMS_LOCK:
            SMS_JOBS[job_id] = {"status": "done", "result": {"phone": phone, "mode": mode, "count": count, "summary": summary, "total_sent": ok, "total_failed": fl}, "source": "SMS Bomber (Zenix)"}
    except Exception as e:
        with SMS_LOCK: SMS_JOBS[job_id] = {"status": "error", "error": str(e)}

# ==================== ROUTES ====================
@app.route('/')
@app.route('/index.html')
@requires_auth
def index():
    return send_from_directory(BASE_DIR, 'encrypted.html')

@app.route('/api/sms/status')
@requires_auth
def sms_status():
    job_id = request.args.get('job_id')
    if not job_id: return jsonify({"status": "error", "error": "job_id eksik"}), 400
    with SMS_LOCK: job = SMS_JOBS.get(job_id)
    if not job: return jsonify({"status": "error", "error": "İş bulunamadı"}), 404
    return jsonify(job)

@app.route('/api')
@requires_auth
def api():
    query_type = request.args.get('type'); query_val = request.args.get('query', '')
    if not query_type: return jsonify({"error": "Eksik parametre"}), 400

    if query_type == "smsbomber":
        if SmsBomber is None: return jsonify({"error": "smsapi.py bulunamadı."}), 500
        count = int(request.args.get('count', 1)); mode = request.args.get('mode', 'turbo')
        job_id = str(uuid.uuid4())
        with SMS_LOCK: SMS_JOBS[job_id] = {"status": "running"}
        threading.Thread(target=_sms_worker, args=(job_id, query_val, count, mode), daemon=True).start()
        return jsonify({"job_id": job_id, "status": "started"})

    target_url = ""
    if query_type == "tc": target_url = f"{PANELABI}/tcsorgu.php?tc={query_val}"
    elif query_type == "tcpro": target_url = f"{PANELABI}/tcsorgupro.php?tc={query_val}"
    elif query_type == "aile": target_url = f"{PANELABI}/aile.php?tc={query_val}"
    elif query_type == "sulale": target_url = f"{PANELABI}/sulale.php?tc={query_val}"
    elif query_type == "adres": target_url = f"{PANELABI}/adres.php?tc={query_val}"
    elif query_type == "isyeri": target_url = f"{PANELABI}/isyeri.php?tc={query_val}"
    elif query_type == "sgk": target_url = f"{PANELABI}/sgk.php?tc={query_val}"
    elif query_type == "tcgsm": target_url = f"{PANELABI}/tcgsm.php?tc={query_val}"
    elif query_type == "gsmtc": target_url = f"{PANELABI}/gsmtc.php?gsm={query_val}"
    elif query_type == "eokulno": target_url = f"{PANELABI}/eokulno.php?tc={query_val}"
    elif query_type == "log": target_url = f"{PANELABI}/log.php?url={query_val}"
    elif query_type == "adsoyad":
        parts = query_val.split(" ")
        if len(parts) < 2: return jsonify({"error": "Ad ve soyad arasında boşluk bırakın."}), 400
        target_url = f"{PANELABI}/adsoyad.php?ad={parts[0]}&soyad={parts[-1]}"
    elif query_type == "adililce":
        parts = query_val.split(" ")
        if len(parts) < 3: return jsonify({"error": "Ad, İl ve İlçe arasında boşluk bırakın."}), 400
        target_url = f"{PANELABI}/adililce.php?ad={parts[0]}&il={parts[1]}&ilce={' '.join(parts[2:])}"
    elif query_type == "vesika": target_url = f"{SOLIDARK}/vesika.php?tc={query_val}"
    elif query_type == "bedrock": target_url = f"{WAZELY}/bedrock?adres={query_val}"
    elif query_type == "ccgen": target_url = f"{WAZELY}/ccgen"
    elif query_type == "cccheck": target_url = f"{WAZELY}/check?data={query_val}"
    elif query_type == "trlog": target_url = f"{WAZELY}/trlog?site={query_val}"
    elif query_type == "eczane": target_url = f"{WAZELY}/eczane?ad={query_val}"
    elif query_type == "ipinfo": target_url = f"{WAZELY}/ipinfo?ip={query_val}"
    elif query_type == "dns": target_url = f"{WAZELY}/dns?domain={query_val}"
    elif query_type == "bahis": target_url = f"{WAZELY}/bahis?isimsoyisim={query_val}"
    elif query_type == "exxengen": target_url = f"{WAZELY}/exxengen"
    elif query_type == "fakeNitro": target_url = f"{WAZELY}/fakeNitro?count={query_val if query_val else 5}"
    elif query_type == "plaka": target_url = f"{WAZELY}/plaka?plate={query_val}"
    elif query_type == "predunyam": target_url = f"{WAZELY}/predunyam"
    elif query_type == "ua": target_url = f"{WAZELY}/randomuseragent"
    elif query_type == "discord": target_url = f"{ID_API}?id={query_val}"
    else: return jsonify({"error": "Geçersiz sorgu tipi"}), 400

    try:
        response, source = proxy_request(target_url)
        if response is None: return jsonify({"error": "API'ye ulaşılamadı."}), 500
        try: data = response.json()
        except Exception: data = response.text
        return jsonify({"result": clean_data(data), "source": source})
    except Exception as e:
        return jsonify({"error": f"Bağlantı hatası: {str(e)}"}), 500

# Local test için
if __name__ == '__main__':
    print("Sunucu Baslatiliyor... http://127.0.0.1:5000")
    app.run(port=5000, threaded=True, debug=True)
