# -*- coding: utf-8 -*-
"""
FreeFire Level Up Bot - Professional Web Dashboard & Real-Time EXP Tracker
Embedded Async Web Server (aiohttp)
Optimized for ultra-smooth operation, zero memory leaks, and dynamic multi-account control.
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Any, Optional
from aiohttp import web
import urllib3
import requests
import httpx
import jwt
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import ReqCLan_pb2
import encode_id_clan_pb2
import data_pb2
import output_pb2
from google.protobuf.json_format import MessageToDict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ═══════════════════════════════════════════════════════════════════
#  DRIFT Folder — Saari HTML files yahan se serve hongi
# ═══════════════════════════════════════════════════════════════════
DRIFT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DRIFT")
TEMPLATE_PATH = os.path.join(DRIFT_DIR, "index.html")

OB = "OB55"
KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])

GAME_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9)",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/octet-stream",
    "X-Unity-Version": "2018.4.11f1",
    "X-GA": "v1 1",
    "ReleaseVersion": OB,
    "Expect": "100-continue"
}

REGION_SERVER_MAP = {
    "IND": ("https://client.ind.freefiremobile.com", "client.ind.freefiremobile.com"),
    "ME":  ("https://clientbp.ggblueshark.com", "clientbp.ggblueshark.com"),
    "VN":  ("https://clientbp.ggpolarbear.com", "clientbp.ggpolarbear.com"),
    "BD":  ("https://clientbp.ggwhitehawk.com", "clientbp.ggwhitehawk.com"),
    "PK":  ("https://clientbp.ggblueshark.com", "clientbp.ggblueshark.com"),
    "SG":  ("https://clientbp.ggpolarbear.com", "clientbp.ggpolarbear.com"),
    "BR":  ("https://client.us.freefiremobile.com", "client.us.freefiremobile.com"),
    "NA":  ("https://client.us.freefiremobile.com", "client.us.freefiremobile.com"),
    "ID":  ("https://clientbp.ggpolarbear.com", "clientbp.ggpolarbear.com"),
    "RU":  ("https://clientbp.ggpolarbear.com", "clientbp.ggpolarbear.com"),
    "TH":  ("https://clientbp.ggpolarbear.com", "clientbp.ggpolarbear.com"),
    "SAC": ("https://client.br.freefiremobile.com", "client.br.freefiremobile.com"),
    "TW":  ("https://client.tw.freefiremobile.com", "client.tw.freefiremobile.com"),
    "CIS": ("https://client.cis.freefiremobile.com", "client.cis.freefiremobile.com"),
}
DEFAULT_SERVER_URL = "https://clientbp.ggblueshark.com"
DEFAULT_HOST = "clientbp.ggblueshark.com"

def encrypt_payload(data):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    return cipher.encrypt(pad(data, AES.block_size))

def get_server_info(region):
    val = REGION_SERVER_MAP.get(str(region).upper(), DEFAULT_SERVER_URL)
    if isinstance(val, tuple):
        return val
    return (val, DEFAULT_HOST)

def get_server_url(region):
    info = get_server_info(region)
    return info[0] if isinstance(info, tuple) else info

def fetch_single_clan(clan_id, region, token_cache):
    server_base, host = get_server_info(region)
    url = f"{server_base}/GetClanInfoByClanID"
    try:
        my_data = encode_id_clan_pb2.MyData()
        my_data.field1 = int(clan_id)
        my_data.field2 = 1
        payload = encrypt_payload(my_data.SerializeToString())
    except Exception as e:
        return {"clan_id": clan_id, "error": f"Protobuf failed: {str(e)}"}

    response = None
    for uid, creds in token_cache.items():
        token = creds.get('token')
        if not token:
            continue
        headers = GAME_HEADERS.copy()
        headers["Authorization"] = f"Bearer {token}" if not token.startswith("Bearer ") else token
        headers["Host"] = host
        try:
            res = requests.post(url, headers=headers, data=payload, verify=False, timeout=15.0)
            if res.status_code == 200:
                response = res
                break
            elif "expired" in res.text.lower() or res.status_code == 401:
                continue
            else:
                response = res
                break
        except Exception:
            continue

    if not response or response.status_code != 200:
        return {"clan_id": clan_id, "error": "All tokens failed or expired"}

    full_response = {}
    resp = None
    try:
        resp = data_pb2.response()
        resp.ParseFromString(response.content)
        full_response = MessageToDict(resp, preserving_proto_field_name=True)
    except Exception:
        pass

    guild_xp = 0
    if resp:
        for field_desc, val in resp.ListFields():
            if field_desc.number == 36 and isinstance(val, int):
                guild_xp = val
                break

    if guild_xp == 0 and full_response:
        guild_xp = int(full_response.get("field_36") or full_response.get("xp") or 0)

    return {
        "captain_id": getattr(resp, "captain_id", 0) if resp else full_response.get("captain_id", 0),
        "clan_id": int(clan_id),
        "clan_level": getattr(resp, "rank", 4) if resp else full_response.get("rank", 4),
        "clan_name": getattr(resp, "special_code", None) if resp else (full_response.get("special_code") or f"Guild_{clan_id}"),
        "current_officer": full_response.get("current_officer", 0),
        "current_members": full_response.get("current_members", 1),
        "max_members": full_response.get("max_members", 50),
        "Total guild xp": int(guild_xp),
        "welcome_message": getattr(resp, "welcome_message", "") if resp else full_response.get("welcome_message", ""),
        "region": region,
        "xp": int(guild_xp),
        "raw_response_bytes": response.content.hex()
    }

async def request_clan_async(jwt_token, clan_id, region):
    server_url = get_server_url(region)
    msg = ReqCLan_pb2.MyMessage()
    msg.field_1 = int(clan_id)
    payload = encrypt_payload(msg.SerializeToString())
    headers = GAME_HEADERS.copy()
    headers["Authorization"] = f"Bearer {jwt_token}" if not jwt_token.startswith("Bearer ") else jwt_token
    url = f"{server_url}/RequestJoinClan"
    async with httpx.AsyncClient(verify=False, timeout=8.0) as client:
        r = await client.post(url, headers=headers, content=payload)
        return r.status_code, r.text

EXP_TABLE: Dict[int, int] = {
    1: 0, 2: 48, 3: 202, 4: 544, 5: 1012, 6: 1844, 7: 2792, 8: 3800,
    9: 4870, 10: 6004, 11: 7192, 12: 8448, 13: 9760, 14: 11140, 15: 12566,
    16: 14060, 17: 15610, 18: 17224, 19: 18902, 20: 20632, 21: 22424, 22: 24278,
    23: 26192, 24: 28166, 25: 30200, 26: 32294, 27: 34448, 28: 37804, 29: 41274,
    30: 44870, 31: 48582, 32: 53394, 33: 58566, 34: 64096, 35: 69994, 36: 76460,
    37: 83506, 38: 91128, 39: 99322, 40: 108092, 41: 120144, 42: 133266, 43: 147472,
    44: 162760, 45: 179126, 46: 196572, 47: 215368, 48: 235516, 49: 257010, 50: 279860,
    51: 304056, 52: 348318, 53: 394982, 54: 444044, 55: 495508, 56: 549364, 57: 633756,
    58: 721744, 59: 813336, 60: 908522, 61: 1041438, 62: 1180352, 63: 1325266,
    64: 1476184, 65: 1634300, 66: 1840946, 67: 2056594, 68: 2281242, 69: 2514880,
    70: 2757530, 71: 3059506, 72: 3372284, 73: 3699456, 74: 4041030, 75: 4397002,
    76: 4829104, 77: 5282204, 78: 5756304, 79: 6251408, 80: 6776502, 81: 7381324,
    82: 8043154, 83: 8752982, 84: 9510808, 85: 10316338, 86: 11277190, 87: 12291748,
    88: 13360304, 89: 14482858, 90: 15659418, 91: 17026708, 92: 18453950, 93: 19941280,
    94: 21488570, 95: 23095858, 96: 24763138, 97: 26490428, 98: 28378704, 99: 30124996,
    100: 32032884
}

async def handle_index(request: web.Request) -> web.Response:
    content = FALLBACK_INDEX_HTML
    if os.path.exists(TEMPLATE_PATH):
        try:
            with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            pass
    return web.Response(text=content, content_type="text/html", charset="utf-8")

async def handle_get_stats(request: web.Request) -> web.Response:
    accounts_data = list(bot_state.accounts.values())
    accounts_data.sort(key=lambda x: x.get("gained_exp", 0), reverse=True)
    uptime_sec = max(1, int(time.time() - bot_state.start_time))
    total_gained = bot_state.total_gained_exp
    exp_per_hour = int((total_gained / uptime_sec) * 3600)
    total_active_matches = sum(acc.get("active_matches", 0) for acc in accounts_data)

    for acc in accounts_data:
        uid_k = str(acc.get("uid", ""))
        acc["uptime_seconds"] = bot_state.get_account_uptime(uid_k)
        acc["is_paused"] = bot_state.is_paused(uid_k)

    return web.json_response({
        "total_accounts": len(bot_state.accounts),
        "total_matches": bot_state.total_matches,
        "total_matches_started": bot_state.total_matches_started,
        "total_active_matches": total_active_matches,
        "total_gained_exp": total_gained,
        "exp_per_hour": exp_per_hour,
        "accounts": accounts_data,
        "logs": bot_state.logs[-80:],
        "uptime": uptime_sec
    })

def calculate_level_progress(level: int, current_exp: int) -> Dict[str, Any]:
    level = max(1, level)
    next_level = min(100, level + 1)
    base_exp = EXP_TABLE.get(level, 0)
    target_exp = EXP_TABLE.get(next_level, base_exp + 50000)
    needed_for_level = max(1, target_exp - base_exp)
    earned_in_level = max(0, current_exp - base_exp)
    remaining_exp = max(0, target_exp - current_exp)
    progress_pct = min(100.0, max(0.0, (earned_in_level / needed_for_level) * 100.0))
    return {
        "next_level": next_level, "base_exp": base_exp, "target_exp": target_exp,
        "needed_for_level": needed_for_level, "earned_in_level": earned_in_level,
        "remaining_exp": remaining_exp, "progress_pct": round(progress_pct, 1)
    }

class BotState:
    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.logs: List[Dict[str, Any]] = []
        self.max_logs = 200
        self.total_matches = 0
        self.total_matches_started = 0
        self.total_gained_exp = 0
        self.start_time = time.time()
        self.account_workers: Dict[str, asyncio.Task] = {}
        self.account_token_map: Dict[str, str] = {}
        self.auth_to_game_id: Dict[str, str] = {}
        self.game_to_auth_id: Dict[str, str] = {}
        self.paused_accounts: set = set()
        self.refresh_callbacks: Dict[str, Any] = {}
        self.account_credentials: Dict[str, Dict[str, Any]] = {}
        self.active_writers: Dict[str, set] = {}

    def register_writer(self, uid: str, writer):
        uid_str = str(uid)
        if uid_str not in self.active_writers: self.active_writers[uid_str] = set()
        self.active_writers[uid_str].add(writer)

    def unregister_writer(self, uid: str, writer):
        uid_str = str(uid)
        if uid_str in self.active_writers:
            self.active_writers[uid_str].discard(writer)
            if not self.active_writers[uid_str]: self.active_writers.pop(uid_str, None)

    def close_writers_for_account(self, uid: str):
        uid_str = str(uid)
        candidates = {uid_str}
        if uid_str in self.auth_to_game_id: candidates.add(str(self.auth_to_game_id[uid_str]))
        if uid_str in self.game_to_auth_id: candidates.add(str(self.game_to_auth_id[uid_str]))
        for c in list(candidates):
            for w in list(self.active_writers.get(c, [])):
                try:
                    if hasattr(w, "close"): w.close()
                except Exception: pass
            self.active_writers.pop(c, None)

    def log(self, message: str, level: str = "info", uid: Optional[str] = None):
        entry = {"time": time.strftime("%H:%M:%S"), "level": level, "message": message, "uid": str(uid) if uid else None}
        self.logs.append(entry)
        if len(self.logs) > self.max_logs: self.logs.pop(0)

    def register_account(self, uid: str, nickname: str, region: str, level: int, exp: int, likes: int = 0, token: Optional[str] = None, auth_uid: Optional[str] = None):
        uid_str = str(uid)
        auth_uid_str = str(auth_uid) if auth_uid else self.game_to_auth_id.get(uid_str, "")
        if auth_uid_str:
            self.auth_to_game_id[auth_uid_str] = uid_str
            self.game_to_auth_id[uid_str] = auth_uid_str
        prog = calculate_level_progress(level or 1, exp)
        lvl_val = level or 1
        if uid_str not in self.accounts:
            self.accounts[uid_str] = {
                "uid": uid_str, "auth_uid": auth_uid_str or "", "nickname": nickname or f"Player_{uid_str[:6]}",
                "region": region or "BD", "level": lvl_val, "next_level": prog["next_level"],
                "mode": "BR" if lvl_val < 3 else "LONE_WOLF", "initial_exp": exp, "current_exp": exp,
                "gained_exp": 0, "remaining_exp": prog["remaining_exp"], "target_exp": prog["target_exp"],
                "needed_for_level": prog["needed_for_level"], "earned_in_level": prog["earned_in_level"],
                "progress_pct": prog["progress_pct"], "likes": likes or 0, "status": "ONLINE",
                "matches_played": 0, "active_matches": 0, "token": token or "", "start_time": time.time(),
                "is_paused": False, "total_pause_duration": 0.0, "last_updated": time.strftime("%H:%M:%S")
            }
        else:
            acc = self.accounts[uid_str]
            acc["current_exp"] = exp
            if level: acc["level"] = level
            acc["gained_exp"] = max(0, exp - acc["initial_exp"])
            acc["next_level"] = prog["next_level"]
            acc["remaining_exp"] = prog["remaining_exp"]
            acc["target_exp"] = prog["target_exp"]
            acc["needed_for_level"] = prog["needed_for_level"]
            acc["earned_in_level"] = prog["earned_in_level"]
            acc["progress_pct"] = prog["progress_pct"]
            acc["likes"] = likes
            acc["last_updated"] = time.strftime("%H:%M:%S")
        self.recalc_totals()

    def get_account_uptime(self, uid_str: str) -> int:
        acc = self.accounts.get(uid_str)
        if not acc: return 0
        return max(0, int(time.time() - acc.get("start_time", time.time()) - acc.get("total_pause_duration", 0.0)))

    def is_paused(self, uid: str) -> bool:
        return str(uid) in self.paused_accounts

    def toggle_pause(self, uid: str) -> bool:
        uid_str = str(uid)
        if self.is_paused(uid_str):
            self.paused_accounts.discard(uid_str)
            return False
        else:
            self.paused_accounts.add(uid_str)
            self.close_writers_for_account(uid_str)
            return True

    def toggle_pause_all(self) -> bool:
        return False

    def update_exp(self, uid: str, current_exp: int, level: Optional[int] = None):
        uid_str = str(uid)
        if uid_str in self.accounts:
            acc = self.accounts[uid_str]
            acc["current_exp"] = current_exp
            if level: acc["level"] = level
            acc["gained_exp"] = max(0, current_exp - acc["initial_exp"])
            prog = calculate_level_progress(acc["level"], current_exp)
            acc["progress_pct"] = prog["progress_pct"]
            self.recalc_totals()

    def update_status(self, uid: str, status: str, active_matches: Optional[int] = None):
        uid_str = str(uid)
        if uid_str in self.accounts:
            self.accounts[uid_str]["status"] = status
            if active_matches is not None: self.accounts[uid_str]["active_matches"] = active_matches

    def increment_match(self, uid: str):
        uid_str = str(uid)
        self.total_matches += 1
        if uid_str in self.accounts:
            self.accounts[uid_str]["matches_played"] += 1

    def recalc_totals(self):
        self.total_gained_exp = sum(acc.get("gained_exp", 0) for acc in self.accounts.values())

bot_state = BotState()
FALLBACK_INDEX_HTML = "<html><body>BOT RUNNING</body></html>"

async def serve_drift_file(filename: str):
    file_path = os.path.join(DRIFT_DIR, filename)
    if not os.path.isfile(file_path):
        return web.Response(status=404, text=f"DRIFT/{filename} not found")
    return web.FileResponse(file_path)

# تحويل فوري ومباشر إلى لوحة التحكم بدون شاشات تحميل
async def handle_ffglory(request: web.Request) -> web.Response:
    raise web.HTTPFound('/client')

async def handle_login_page(request: web.Request) -> web.Response:
    raise web.HTTPFound('/client')

async def handle_client_page(request: web.Request) -> web.Response:
    return await serve_drift_file("client.html")

async def handle_bot_page(request: web.Request) -> web.Response:
    return await serve_drift_file("index.html")

# ═══════════════════════════════════════════════════════════════════
#  APIs المحدثة لمنع تعليق Loading في الواجهة
# ═══════════════════════════════════════════════════════════════════
async def handle_api_me(request: web.Request) -> web.Response:
    return web.json_response({
        "username": "admin", "role": "admin",
        "basic_credits": 1000, "premium_credits": 500, "max_groups": 10
    })

async def handle_api_pricing(request: web.Request) -> web.Response:
    return web.json_response({
        "basic_credit_usd": 1.70, "premium_credit_usd": 20.00,
        "regions": [
            {"id": "ind", "region_name": "India", "tier": "basic", "enabled": True},
            {"id": "bd", "region_name": "Bangladesh", "tier": "basic", "enabled": True},
            {"id": "me", "region_name": "Middle East", "tier": "premium", "enabled": True},
            {"id": "br", "region_name": "Brasil", "tier": "premium", "enabled": True}
        ]
    })

async def handle_api_client_groups(request: web.Request) -> web.Response:
    return web.json_response([])

async def handle_api_transactions(request: web.Request) -> web.Response:
    return web.json_response([])

async def handle_api_activity_log(request: web.Request) -> web.Response:
    return web.json_response([])

async def handle_api_notifications(request: web.Request) -> web.Response:
    return web.json_response([])

async def handle_api_inbox_messages(request: web.Request) -> web.Response:
    return web.json_response([])

async def handle_api_my_coupons(request: web.Request) -> web.Response:
    return web.json_response([])

async def handle_api_redeemed_coupons(request: web.Request) -> web.Response:
    return web.json_response([])

async def handle_api_active_alert(request: web.Request) -> web.Response:
    return web.json_response({})

async def handle_api_logout(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_api_signup(request: web.Request) -> web.Response:
    return web.json_response({"success": True})

async def handle_api_login(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_api_clan_join(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_add_account(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_delete_account(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_refresh_account(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_restart_account(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_clear_logs(request: web.Request) -> web.Response:
    bot_state.logs.clear()
    return web.json_response({"status": "ok"})

async def handle_toggle_pause(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_toggle_pause_all(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def handle_api_logs(request: web.Request) -> web.Response:
    return web.json_response({"logs": []})

async def start_web_dashboard(host: str = "0.0.0.0", port: int = 5000):
    app = web.Application()

    app.router.add_get("/",       handle_ffglory)
    app.router.add_get("/login",  handle_login_page)
    app.router.add_get("/client", handle_client_page)
    app.router.add_get("/bot",    handle_bot_page)

    app.router.add_get("/api/me", handle_api_me)
    app.router.add_get("/api/pricing", handle_api_pricing)
    app.router.add_get("/api/client/groups", handle_api_client_groups)
    app.router.add_get("/api/transactions", handle_api_transactions)
    app.router.add_get("/api/client/activity-log", handle_api_activity_log)
    app.router.add_get("/api/notifications", handle_api_notifications)
    app.router.add_get("/api/inbox/messages", handle_api_inbox_messages)
    app.router.add_get("/api/coupons/mine", handle_api_my_coupons)
    app.router.add_get("/api/coupons/redeemed", handle_api_redeemed_coupons)
    app.router.add_get("/api/client/active-alert", handle_api_active_alert)
    app.router.add_get("/api/stats", handle_get_stats)
    app.router.add_get("/api/logs", handle_api_logs)

    app.router.add_post("/api/auth/login", handle_api_login)
    app.router.add_post("/api/auth/signup", handle_api_signup)
    app.router.add_post("/api/logout", handle_api_logout)
    app.router.add_post("/api/clanjoin", handle_api_clan_join)
    app.router.add_post("/api/account/add", handle_add_account)
    app.router.add_post("/api/account/delete", handle_delete_account)
    app.router.add_post("/api/account/refresh", handle_refresh_account)
    app.router.add_post("/api/account/restart", handle_restart_account)
    app.router.add_post("/api/account/pause", handle_toggle_pause)
    app.router.add_post("/api/account/pause_all", handle_toggle_pause_all)
    app.router.add_post("/api/logs/clear", handle_clear_logs)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner
