from flask import Flask, request, jsonify
import requests
import asyncio
import random
import threading
import uuid
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from smsapi import SmsBomber
except ImportError:
    try:
        from ..smsapi import SmsBomber
    except ImportError:
        SmsBomber = None

app = Flask(__name__)

# ==================== API ADRESLERİ ====================
PANELABI = "https://api.panelabi.top"
SOLIDARK = "https://solidarksystems.alwaysdata.net"
WAZELY = "https://wazely.vercel.app/api"
WAZELY_API = "https://wazelyapi.vercel.app/api"
ID_API = "https://prox0959.netlify.app/api/search"

# ==================== PROXY HAVUZU ====================
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

# ==================== SMS BOMBER İŞ HAVUZU ====================
SMS_JOBS = {}
SMS_LOCK = threading.Lock()

def clean_data(obj):
    if isinstance(obj, list):
        return [clean_data(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_data(v) for k, v in obj.items()
                if k.lower() not in ('author', 'auth', 'auth_alt', 'dev', 'credit', 'instagram', 'ig')}
    if isinstance(obj, str):
        for bad in ["@jessy_php", "jessy", "@wazelybaba", "wazely"]:
            obj = obj.replace(bad, "")
        return obj.strip()
    return obj

def proxy_request(url, timeout=5):
    shuffled = USER_PROXIES[:]
    random.shuffle(shuffled)
    for p in shuffled:
        try:
            proxy_url = f"http://{p['user']}:{p['pass']}@{p['ip']}:{p['port']}"
            proxies = {"http": proxy_url, "https": proxy_url}
            r = requests.get(url, proxies=proxies, timeout=timeout,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                return r, "Kendi Proxy"
        except Exception:
            continue
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            return r, "Doğrudan Bağlantı (Proxy çöktü)"
    except Exception:
        pass
    return None, None

async def _run_turbo_limited(bomber, adet, max_concurrent=10):
    services = bomber.get_services()
    sem = asyncio.Semaphore(max_concurrent)
    async def run_one(svc):
        async with sem:
            try:
                await asyncio.to_thread(svc)
            except Exception:
                pass
    for _ in range(adet):
        tasks = [run_one(svc) for svc in services]
        await asyncio.gather(*tasks)

def _sms_worker(job_id, phone, count, mode):
    try:
        b = SmsBomber(phone)
        if mode == 'turbo':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run_turbo_limited(b, count, max_concurrent=10))
            loop.close()
        else:
            b.run_normal(count)
        summary = {}
        for n, s in b.results:
            summary.setdefault(n, {"ok": 0, "fail": 0})
            if s:
                summary[n]["ok"] += 1
            else:
                summary[n]["fail"] += 1
        ok = sum(1 for _, v in b.results if v)
        fl = len(b.results) - ok
        with SMS_LOCK:
            SMS_JOBS[job_id] = {
                "status": "done",
                "result": {
                    "phone": phone, "mode": mode, "count": count,
                    "summary": summary, "total_sent": ok, "total_failed": fl
                },
                "source": "SMS Bomber (Zenix)"
            }
    except Exception as e:
        with SMS_LOCK:
            SMS_JOBS[job_id] = {"status": "error", "error": f"SMS Bomber Hatası: {str(e)}"}

@app.route('/api/sms/status')
def sms_status():
    job_id = request.args.get('job_id')
    if not job_id:
        return jsonify({"status": "error", "error": "job_id eksik"}), 400
    with SMS_LOCK:
        job = SMS_JOBS.get(job_id)
    if not job:
        return jsonify({"status": "error", "error": "İş bulunamadı"}), 404
    return jsonify(job)

@app.route('/api')
def api():
    query_type = request.args.get('type')
    query_val = request.args.get('query', '')
    if not query_type:
        return jsonify({"error": "Eksik parametre"}), 400

    # ==================== SMS BOMBER ====================
    if query_type == "smsbomber":
        if SmsBomber is None:
            return jsonify({"error": "smsapi.py bulunamadı."}), 500
        count = int(request.args.get('count', 1))
        mode = request.args.get('mode', 'turbo')
        job_id = str(uuid.uuid4())
        with SMS_LOCK:
            SMS_JOBS[job_id] = {"status": "running"}
        t = threading.Thread(target=_sms_worker, args=(job_id, query_val, count, mode), daemon=True)
        t.start()
        return jsonify({"job_id": job_id, "status": "started"})

    target_url = ""
    source_name = ""

    # ==================== PANELABI ====================
    if query_type in ["tc", "tcpro", "aile", "sulale", "adres", "isyeri", "sgk"]:
        target_url = f"{PANELABI}/{query_type if query_type != 'tcpro' else 'tcsorgupro'}.php?tc={query_val}"
        source_name = "PanelAbi"
    elif query_type == "tcgsm":
        target_url = f"{PANELABI}/tcgsm.php?tc={query_val}"
        source_name = "PanelAbi"
    elif query_type == "gsmtc":
        target_url = f"{PANELABI}/gsmtc.php?gsm={query_val}"
        source_name = "PanelAbi"
    elif query_type == "eokulno":
        target_url = f"{PANELABI}/eokulno.php?tc={query_val}"
        source_name = "PanelAbi"
    elif query_type == "log":
        target_url = f"{PANELABI}/log.php?url={query_val}"
        source_name = "PanelAbi"
    elif query_type == "adsoyad":
        parts = query_val.split(" ")
        if len(parts) < 2: return jsonify({"error": "Ad ve soyad arasında boşluk bırakın."}), 400
        target_url = f"{PANELABI}/adsoyad.php?ad={parts[0]}&soyad={parts[-1]}"
        source_name = "PanelAbi"
    elif query_type == "adililce":
        parts = query_val.split(" ")
        if len(parts) < 3: return jsonify({"error": "Ad, İl ve İlçe arasında boşluk bırakın."}), 400
        target_url = f"{PANELABI}/adililce.php?ad={parts[0]}&il={parts[1]}&ilce={' '.join(parts[2:])}"
        source_name = "PanelAbi"

    # ==================== SOLIDARK (Vesika) ====================
    elif query_type == "vesika":
        target_url = f"{SOLIDARK}/vesika.php?tc={query_val}"
        source_name = "Solidark"

    # ==================== WAZELY (Genel) ====================
    elif query_type == "trlog":
        target_url = f"{WAZELY}/trlog?site={query_val}"
        source_name = "Wazely"
    elif query_type == "eczane":
        target_url = f"{WAZELY}/eczane?ad={query_val}"
        source_name = "Wazely"
    elif query_type == "ipinfo":
        target_url = f"{WAZELY}/ipinfo?ip={query_val}"
        source_name = "Wazely"
    elif query_type == "dns":
        target_url = f"{WAZELY}/dns?domain={query_val}"
        source_name = "Wazely"
    elif query_type == "bahis":
        target_url = f"{WAZELY}/bahis?isimsoyisim={query_val}"
        source_name = "Wazely"
    elif query_type == "exxengen":
        target_url = f"{WAZELY}/exxengen"
        source_name = "Wazely"
    elif query_type == "fakeNitro":
        target_url = f"{WAZELY}/fakeNitro?count={query_val if query_val else 5}"
        source_name = "Wazely"
    elif query_type == "ping":
        target_url = f"{WAZELY}/ping?target={query_val}"
        source_name = "Wazely"
    elif query_type == "plaka":
        target_url = f"{WAZELY}/plaka?plate={query_val}"
        source_name = "Wazely"
    elif query_type == "predunyam":
        target_url = f"{WAZELY}/predunyam"
        source_name = "Wazely"
    elif query_type == "ua":
        target_url = f"{WAZELY}/randomuseragent"
        source_name = "Wazely"

    # ==================== WAZELY API (Özel) ====================
    elif query_type == "bedrock":
        target_url = f"{WAZELY_API}/bedrock?adres={query_val}"
        source_name = "WazelyAPI"
    elif query_type == "ccgen":
        target_url = f"{WAZELY_API}/ccgen"
        source_name = "WazelyAPI"
    elif query_type == "cccheck":
        target_url = f"{WAZELY_API}/check?data={query_val}"
        source_name = "WazelyAPI"
    elif query_type == "dcbottokencheck":
        target_url = f"{WAZELY_API}/dcbottokencheck?token={query_val}"
        source_name = "WazelyAPI"
    elif query_type == "tgtokencheck":
        target_url = f"{WAZELY_API}/tgtokencheck?token={query_val}"
        source_name = "WazelyAPI"

    # ==================== ID API ====================
    elif query_type == "discord":
        target_url = f"{ID_API}?id={query_val}"
        source_name = "ID API"

    else:
        return jsonify({"error": "Geçersiz sorgu tipi"}), 400

    # ==================== İSTEK AT ====================
    try:
        response, proxy_source = proxy_request(target_url)
        if response is None:
            return jsonify({"error": "API'ye ulaşılamadı. Proxy'ler ve doğrudan bağlantı başarısız."}), 500

        try:
            data = response.json()
        except Exception:
            data = response.text

        data = clean_data(data)
        final_source = f"{source_name} ({proxy_source})" if proxy_source else source_name
        return jsonify({"result": data, "source": final_source})
    except Exception as e:
        return jsonify({"error": f"Bağlantı hatası: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5000, threaded=True)
