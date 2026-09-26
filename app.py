import os
import re
import json
import uuid
import imaplib
import email
from email.header import decode_header
import email.utils
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, 'accounts.json')
HTML_FILE = 'index.html' if os.path.exists(os.path.join(BASE_DIR, 'index.html')) else 'personal_email_dashboard.html'

# Dukungan Vercel Serverless (Filesystem selain /tmp bersifat read-only)
if os.environ.get('VERCEL'):
    TMP_ACCOUNTS = '/tmp/accounts.json'
    if not os.path.exists(TMP_ACCOUNTS):
        if os.environ.get('ACCOUNTS_JSON'):
            try:
                with open(TMP_ACCOUNTS, 'w', encoding='utf-8') as f:
                    f.write(os.environ.get('ACCOUNTS_JSON'))
            except Exception as e:
                print(f"Error initializing ACCOUNTS_JSON on Vercel: {e}")
        elif os.path.exists(ACCOUNTS_FILE):
            try:
                import shutil
                shutil.copyfile(ACCOUNTS_FILE, TMP_ACCOUNTS)
            except Exception as e:
                print(f"Error copying accounts to /tmp on Vercel: {e}")
    ACCOUNTS_FILE = TMP_ACCOUNTS

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

# Middleware WSGI untuk Vercel: Mengembalikan PATH_INFO asli jika melalui rewrites
class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI')
        if matched:
            environ['PATH_INFO'] = matched.split('?')[0]
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

# Helper: Auto-deteksi server IMAP berdasarkan domain email
def detect_imap_server(email_address):
    domain = email_address.lower().split('@')[-1] if '@' in email_address else ''
    if domain in ['gmail.com', 'googlemail.com']:
        return 'imap.gmail.com', 993
    elif domain in ['hotmail.com', 'outlook.com', 'live.com', 'msn.com', 'windowslive.com']:
        return 'outlook.office365.com', 993
    elif domain in ['yahoo.com', 'ymail.com']:
        return 'imap.mail.yahoo.com', 993
    return 'imap.' + domain, 993

# Helper: Load accounts dari accounts.json
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Pastikan setiap akun memiliki ID unik dan server default jika kosong
            for acc in data:
                if 'id' not in acc:
                    acc['id'] = str(uuid.uuid4())[:8]
                if not acc.get('server'):
                    srv, port = detect_imap_server(acc.get('email', ''))
                    acc['server'] = srv
                    acc['port'] = port
            return data
    except Exception as e:
        print(f"Error loading accounts: {e}")
        return []

# Helper: Save accounts ke accounts.json
def save_accounts(accounts):
    try:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving accounts: {e}")
        return False

# Helper: Dekode MIME header (mendukung multi-chunk dan variasi charset)
def decode_mime_words(raw_header):
    if not raw_header:
        return ""
    try:
        decoded_fragments = decode_header(raw_header)
        pieces = []
        for text, enc in decoded_fragments:
            if isinstance(text, bytes):
                encoding = enc if enc else 'utf-8'
                try:
                    pieces.append(text.decode(encoding, errors='replace'))
                except LookupError:
                    pieces.append(text.decode('utf-8', errors='replace'))
            else:
                pieces.append(str(text))
        return "".join(pieces).strip()
    except Exception:
        return str(raw_header)

# Helper: Parsing sender (nama & email)
def parse_sender(raw_from):
    if not raw_from:
        return "Unknown Sender", ""
    name, addr = email.utils.parseaddr(raw_from)
    name = decode_mime_words(name)
    addr = decode_mime_words(addr)
    if not name:
        name = addr.split('@')[0] if '@' in addr else addr
    return name, addr

# Helper: Parsing tanggal email
def parse_email_date(date_header):
    if not date_header:
        now = datetime.now(timezone.utc)
        return now.isoformat(), int(now.timestamp()), "Waktu tidak diketahui"
    try:
        parsed_dt = email.utils.parsedate_to_datetime(date_header)
        if parsed_dt.tzinfo is None:
            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
        iso = parsed_dt.isoformat()
        ts = int(parsed_dt.timestamp())
        # Format ramah lokal
        display_str = parsed_dt.strftime("%d %b %Y %H:%M")
        return iso, ts, display_str
    except Exception:
        now = datetime.now(timezone.utc)
        return now.isoformat(), int(now.timestamp()), str(date_header)[:25]

# Helper: Ekstraksi snippet dan body email
def extract_email_content(msg):
    snippet = ""
    body_plain = ""
    body_html = ""
    attachments = []

    try:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                filename = part.get_filename()

                if filename:
                    filename = decode_mime_words(filename)
                    size = len(part.get_payload(decode=True) or b"")
                    attachments.append({
                        "filename": filename,
                        "size": size,
                        "type": content_type
                    })
                    continue

                if "attachment" in content_disposition.lower():
                    continue

                if content_type == "text/plain" and not body_plain:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body_plain = payload.decode(charset, errors='replace')
                        except LookupError:
                            body_plain = payload.decode('utf-8', errors='replace')

                elif content_type == "text/html" and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body_html = payload.decode(charset, errors='replace')
                        except LookupError:
                            body_html = payload.decode('utf-8', errors='replace')
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                try:
                    text = payload.decode(charset, errors='replace')
                except LookupError:
                    text = payload.decode('utf-8', errors='replace')
                if content_type == "text/html":
                    body_html = text
                else:
                    body_plain = text

        # Buat snippet ringkas untuk tampilan daftar kartu
        if body_plain:
            clean_text = " ".join(body_plain.split())
            snippet = clean_text[:160]
        elif body_html:
            clean_text = re.sub(r'<[^>]+>', ' ', body_html)
            clean_text = " ".join(clean_text.split())
            snippet = clean_text[:160]

        if len(snippet) >= 160:
            snippet += "..."

    except Exception as e:
        print(f"Error extracting body: {e}")
        snippet = "(Pratinjau pesan tidak tersedia)"

    return snippet, body_plain, body_html, attachments

# Helper: Ekstraksi kode verifikasi / OTP dari subjek dan isi email
def extract_verification_code(subject, body_plain, body_html=""):
    text = f"{subject or ''}\n{body_plain or ''}"
    if not text.strip() and body_html:
        clean_html = re.sub(r'<[^>]+>', ' ', body_html)
        text = f"{subject or ''}\n{clean_html}"

    text_lower = text.lower()

    # Kata kunci penanda email verifikasi / kode
    keywords = [
        'kode', 'code', 'otp', 'pin', 'verifikasi', 'verification',
        'passcode', 'security', 'keamanan', 'aktivasi', 'activation',
        'konfirmasi', 'confirmation', 'sandi', 'password', 'login'
    ]
    has_keyword = any(kw in text_lower for kw in keywords)
    if not has_keyword:
        return None

    # 1. Format G-XXXXXX (Google)
    m = re.search(r'\b(G-\d{6})\b', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # 2. Pola eksplisit kode: 'kode anda: 123456' / 'code is: 123456'
    explicit_patterns = [
        r'(?:kode|code|otp|pin|passcode|verifikasi|verification)[\s\w]*?[:=\-–#]\s*([A-Z0-9]{4,8})\b',
        r'(?:kode|code|otp|pin|passcode)\s+(?:anda|kamu|is|adalah|to|for)[\s\w]*?\s+([A-Z0-9]{4,8})\b',
        r'\b([0-9]{6})\b',  # 6 digit angka standar OTP
        r'\b([0-9]{4,8})\b'
    ]

    for pat in explicit_patterns:
        matches = re.finditer(pat, text, re.IGNORECASE)
        for match in matches:
            val = match.group(1).strip()
            # Lewati angka yang mirip tahun kalender
            if val in ['2023', '2024', '2025', '2026', '2027']:
                continue
            return val

    return None

# Helper: Validasi pengirim khusus (Hanya Facebook, Google, dan Microsoft Account Team)
def check_target_sender(sender_name, sender_email):
    n = (sender_name or '').lower()
    a = (sender_email or '').lower()

    # 1. Google
    if 'google' in n or 'google' in a:
        return True, 'google', 'Google'

    # 2. Facebook / Meta
    if any(k in n for k in ['facebook', 'meta']) or any(k in a for k in ['facebookmail.com', 'facebook.com', 'meta.com']):
        return True, 'facebook', 'Facebook'

    # 3. Microsoft Account Team
    if any(k in n for k in ['microsoft', 'windows live', 'live.com']) or any(k in a for k in ['microsoft.com', 'accountprotection.microsoft.com']):
        return True, 'microsoft', 'Microsoft'

    return False, None, None

# Fungsi fetch email per akun
def fetch_account_emails(account, mode="unseen", limit=10, sender_filter="all", max_minutes=120):
    account_email = account.get("email", "")
    server = account.get("server") or detect_imap_server(account_email)[0]
    port = int(account.get("port", 993))
    password = account.get("password", "")
    account_id = account.get("id", account_email)
    account_name = account.get("name", account_email)

    domain = account_email.split('@')[-1].lower() if '@' in account_email else ''
    provider = "gmail" if "gmail" in domain else ("hotmail" if any(h in domain for h in ['hotmail', 'outlook', 'live']) else "other")

    res_data = {
        "account_id": account_id,
        "account_name": account_name,
        "account_email": account_email,
        "provider": provider,
        "status": "connected",
        "error_message": None,
        "unread_count": 0,
        "emails": []
    }

    if not account_email or not password:
        res_data["status"] = "error"
        res_data["error_message"] = "Email atau password/sandi aplikasi belum diisi."
        return res_data

    mail = None
    try:
        # Koneksi dengan timeout agar tidak hang
        mail = imaplib.IMAP4_SSL(server, port)
        mail.login(account_email, password)
        status, _ = mail.select("INBOX", readonly=True)
        if status != "OK":
            raise Exception("Gagal memilih folder INBOX")

        # Cek jumlah total UNSEEN
        status, unseen_msg = mail.uid('search', None, 'UNSEEN')
        unseen_uids = unseen_msg[0].split() if (status == "OK" and unseen_msg[0]) else []
        res_data["unread_count"] = len(unseen_uids)

        # Ambil hingga 80 email terbaru untuk disaring
        scan_limit = max(limit * 5, 80)

        target_uids = []
        if mode == "unseen":
            target_uids = unseen_uids[-scan_limit:]
        else: # "all"
            status, all_msg = mail.uid('search', None, 'ALL')
            all_uids = all_msg[0].split() if (status == "OK" and all_msg[0]) else []
            target_uids = all_uids[-scan_limit:]

        now_ts = int(datetime.now(timezone.utc).timestamp())
        emails = []
        for uid in reversed(target_uids):
            uid_str = uid.decode()

            # Langkah 1: Cek header terlebih dahulu (sangat ringan dan cepat tanpa download body)
            res, hdr_data = mail.uid('fetch', uid, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
            if res != "OK" or not hdr_data:
                continue

            raw_header = b""
            for p in hdr_data:
                if isinstance(p, tuple):
                    raw_header = p[1]
                    break

            hdr_msg = email.message_from_bytes(raw_header)

            # Cek batasan waktu (Hanya pesan maksimal max_minutes terbaru)
            iso_date, timestamp, date_str = parse_email_date(hdr_msg.get("Date", ""))
            diff_minutes = (now_ts - timestamp) / 60

            if max_minutes > 0 and diff_minutes > max_minutes:
                # Jika pesan sudah terlalu lama (> 60 menit), hentikan pemindaian pesan sebelumnya
                if diff_minutes > max(max_minutes * 3, 60):
                    break
                continue

            sender_name, sender_email = parse_sender(hdr_msg.get("From", ""))

            # Validasi HANYA Facebook, Google, atau Microsoft Account Team
            is_allowed, sender_tag, sender_label = check_target_sender(sender_name, sender_email)
            if not is_allowed:
                continue

            # Filter sub-kategori jika dipilih (misal: hanya google / hanya facebook / hanya microsoft)
            if sender_filter and sender_filter != "all" and sender_tag != sender_filter:
                continue

            # Format waktu relatif (misal: "Baru saja", "12 mnt lalu")
            if diff_minutes < 1:
                rel_time = "Baru saja"
            elif diff_minutes < 60:
                rel_time = f"{int(diff_minutes)} mnt lalu"
            else:
                rel_time = date_str

            # Langkah 2: Hanya ambil body lengkap jika kriteria cocok
            res, msg_data = mail.uid('fetch', uid, '(RFC822)')
            if res != "OK" or not msg_data:
                continue

            for part in msg_data:
                if isinstance(part, tuple):
                    msg = email.message_from_bytes(part[1])
                    subject = decode_mime_words(msg.get("Subject", "(Tanpa Subjek)"))
                    snippet, body_plain, body_html, attachments = extract_email_content(msg)

                    emails.append({
                        "uid": uid_str,
                        "account_id": account_id,
                        "account_name": account_name,
                        "account_email": account_email,
                        "provider": provider,
                        "sender_tag": sender_tag,       # 'facebook' | 'google' | 'microsoft'
                        "sender_label": sender_label,   # 'Facebook' | 'Google' | 'Microsoft'
                        "sender_name": sender_name,
                        "sender_email": sender_email,
                        "subject": subject or "(Tanpa Subjek)",
                        "snippet": snippet,
                        "date_iso": iso_date,
                        "timestamp": timestamp,
                        "date_str": date_str,
                        "rel_time": rel_time,
                        "diff_minutes": round(diff_minutes, 1),
                        "has_attachments": len(attachments) > 0,
                        "attachment_count": len(attachments),
                        "is_unread": uid in unseen_uids
                    })

                    if len(emails) >= limit:
                        break

            if len(emails) >= limit:
                break

        res_data["emails"] = emails

    except imaplib.IMAP4.error as e:
        res_data["status"] = "auth_error"
        err_str = str(e)
        if "AUTHENTICATE failed" in err_str or "Basic authentication is disabled" in err_str:
            res_data["error_message"] = "Microsoft memblokir Basic Auth/App Password untuk Hotmail pribadi (Gunakan fitur Forwarding ke Gmail)."
        elif "AUTHENTICATIONFAILED" in err_str.upper() or "LOGIN" in err_str.upper():
            res_data["error_message"] = "Autentikasi gagal. Pastikan 2FA aktif dan gunakan 'Sandi Aplikasi' (App Password)."
        else:
            res_data["error_message"] = f"Gagal masuk server IMAP: {err_str}"
    except Exception as e:
        res_data["status"] = "connection_error"
        res_data["error_message"] = f"Koneksi gagal: {str(e)}"
    finally:
        if mail:
            try:
                mail.close()
            except Exception:
                pass
            try:
                mail.logout()
            except Exception:
                pass

    return res_data

# Route utama: Render dashboard HTML langsung
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, HTML_FILE)

# Route helper: Bookmarklet installer page
@app.route('/bookmarklet_installer.html')
@app.route('/tools/bookmarklet')
def bookmarklet_page():
    return send_from_directory(BASE_DIR, 'bookmarklet_installer.html')

# API: Ambil semua email dari semua akun aktif secara paralel
@app.route('/emails', methods=['GET'])
@app.route('/api/emails', methods=['GET'])
def get_emails():
    mode = request.args.get('mode', 'unseen') # 'unseen' atau 'all'
    limit = int(request.args.get('limit', 10))
    sender_filter = request.args.get('sender', 'all').lower().strip()
    max_minutes = int(request.args.get('minutes', 120)) # Paten: maksimal 2 jam terakhir (120 menit)

    accounts = load_accounts()
    active_accounts = [acc for acc in accounts if acc.get('active', True)]

    if not active_accounts:
        return jsonify({
            "success": True,
            "total_accounts": 0,
            "total_unread": 0,
            "accounts_status": [],
            "emails": []
        })

    accounts_status = []
    all_emails = []
    total_unread = 0

    max_workers = min(len(active_accounts), 8) or 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_account_emails, acc, mode, limit, sender_filter, max_minutes) for acc in active_accounts]
        for future in futures:
            res = future.result()
            accounts_status.append({
                "account_id": res["account_id"],
                "account_name": res["account_name"],
                "account_email": res["account_email"],
                "provider": res["provider"],
                "status": res["status"],
                "error_message": res["error_message"],
                "unread_count": res["unread_count"]
            })
            total_unread += res["unread_count"]
            all_emails.extend(res["emails"])

    # Urutkan email gabungan berdasarkan waktu terbaru (timestamp descending)
    all_emails.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    return jsonify({
        "success": True,
        "total_accounts": len(active_accounts),
        "total_unread": total_unread,
        "accounts_status": accounts_status,
        "emails": all_emails
    })

# API: Ambil detail lengkap 1 email (termasuk full body HTML / text) untuk modal preview
@app.route('/email/detail', methods=['GET'])
@app.route('/api/email/detail', methods=['GET'])
def get_email_detail():
    account_id = request.args.get('account_id')
    uid = request.args.get('uid')

    if not account_id or not uid:
        return jsonify({"success": False, "error": "Parameter account_id dan uid wajib diisi"}), 400

    accounts = load_accounts()
    target_acc = next((a for a in accounts if str(a.get('id')) == str(account_id) or a.get('email') == account_id), None)
    if not target_acc:
        return jsonify({"success": False, "error": "Akun tidak ditemukan"}), 404

    server = target_acc.get("server") or detect_imap_server(target_acc.get("email"))[0]
    port = int(target_acc.get("port", 993))

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(server, port)
        mail.login(target_acc["email"], target_acc["password"])
        mail.select("INBOX", readonly=True)

        res, msg_data = mail.uid('fetch', uid.encode(), '(RFC822)')
        if res != "OK" or not msg_data:
            return jsonify({"success": False, "error": "Email tidak ditemukan di server"}), 404

        for part in msg_data:
            if isinstance(part, tuple):
                msg = email.message_from_bytes(part[1])
                subject = decode_mime_words(msg.get("Subject", "(Tanpa Subjek)"))
                sender_name, sender_email = parse_sender(msg.get("From", ""))
                to_name, to_email = parse_sender(msg.get("To", target_acc["email"]))
                iso_date, timestamp, date_str = parse_email_date(msg.get("Date", ""))
                snippet, body_plain, body_html, attachments = extract_email_content(msg)

                return jsonify({
                    "success": True,
                    "email": {
                        "uid": uid,
                        "account_id": target_acc.get("id"),
                        "account_email": target_acc["email"],
                        "subject": subject,
                        "sender_name": sender_name,
                        "sender_email": sender_email,
                        "recipient": f"{to_name} <{to_email}>" if to_name else to_email,
                        "date_str": date_str,
                        "date_iso": iso_date,
                        "body_plain": body_plain,
                        "body_html": body_html,
                        "attachments": attachments
                    }
                })

        return jsonify({"success": False, "error": "Format data email tidak valid"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if mail:
            try:
                mail.close()
            except Exception:
                pass
            try:
                mail.logout()
            except Exception:
                pass

# API: Dapatkan daftar akun (password disensor untuk keamanan)
@app.route('/accounts', methods=['GET'])
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = load_accounts()
    sanitized = []
    for acc in accounts:
        srv, port = detect_imap_server(acc.get("email", ""))
        sanitized.append({
            "id": acc.get("id"),
            "name": acc.get("name", acc.get("email")),
            "email": acc.get("email"),
            "server": acc.get("server") or srv,
            "port": acc.get("port") or port,
            "active": acc.get("active", True),
            "has_password": bool(acc.get("password"))
        })
    return jsonify({"success": True, "accounts": sanitized})

# API: Tambah atau update akun
@app.route('/accounts', methods=['POST'])
@app.route('/api/accounts', methods=['POST'])
def save_account():
    data = request.json or {}
    email_addr = data.get("email", "").strip()
    password = data.get("password", "").strip()
    name = data.get("name", "").strip() or email_addr
    server = data.get("server", "").strip()
    port = data.get("port")
    active = data.get("active", True)
    acc_id = data.get("id")

    if not email_addr:
        return jsonify({"success": False, "error": "Alamat email wajib diisi"}), 400

    default_srv, default_port = detect_imap_server(email_addr)
    server = server or default_srv
    port = int(port) if port else default_port

    accounts = load_accounts()
    existing = next((a for a in accounts if a.get("id") == acc_id), None)

    if existing:
        existing["name"] = name
        existing["email"] = email_addr
        existing["server"] = server
        existing["port"] = port
        existing["active"] = active
        if password: # update jika diisi
            existing["password"] = password
    else:
        if not password:
            return jsonify({"success": False, "error": "Sandi Aplikasi / Password wajib diisi untuk akun baru"}), 400
        new_account = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "email": email_addr,
            "password": password,
            "server": server,
            "port": port,
            "active": active
        }
        accounts.append(new_account)

    if save_accounts(accounts):
        return jsonify({"success": True, "message": "Akun berhasil disimpan"})
    else:
        return jsonify({"success": False, "error": "Gagal menyimpan akun ke file"}), 500

# API: Hapus akun
@app.route('/accounts/<account_id>', methods=['DELETE'])
@app.route('/api/accounts/<account_id>', methods=['DELETE'])
def delete_account(account_id):
    accounts = load_accounts()
    filtered = [a for a in accounts if str(a.get("id")) != str(account_id) and a.get("email") != account_id]
    if len(filtered) == len(accounts):
        return jsonify({"success": False, "error": "Akun tidak ditemukan"}), 404

    if save_accounts(filtered):
        return jsonify({"success": True, "message": "Akun berhasil dihapus"})
    else:
        return jsonify({"success": False, "error": "Gagal menyimpan perubahan"}), 500

# API: Tes koneksi akun
@app.route('/accounts/test', methods=['POST'])
@app.route('/api/accounts/test', methods=['POST'])
def test_account_connection():
    data = request.json or {}
    email_addr = data.get("email", "").strip()
    password = data.get("password", "").strip()
    server = data.get("server", "").strip()
    port = int(data.get("port", 993))

    # Jika password tidak dikirim, ambil dari akun yang sudah ada
    if not password and data.get("id"):
        accounts = load_accounts()
        existing = next((a for a in accounts if a.get("id") == data.get("id")), None)
        if existing:
            password = existing.get("password", "")

    if not email_addr or not password:
        return jsonify({"success": False, "error": "Email dan sandi aplikasi wajib diisi"}), 400

    if not server:
        server, _ = detect_imap_server(email_addr)

    try:
        mail = imaplib.IMAP4_SSL(server, port)
        mail.login(email_addr, password)
        status, _ = mail.select("INBOX", readonly=True)
        mail.logout()
        return jsonify({"success": True, "message": f"Koneksi ke {server} berhasil! Folder INBOX terbaca."})
    except imaplib.IMAP4.error as e:
        err = str(e)
        return jsonify({
            "success": False,
            "error": "Gagal Login (Autentikasi Ditolak). Untuk Gmail/Hotmail, wajib gunakan App Password (Sandi Aplikasi), bukan sandi akun biasa."
        }), 400
# Fallback API handler untuk Vercel Serverless routing
@app.route('/api/index', methods=['GET', 'POST', 'DELETE'])
@app.route('/api', methods=['GET', 'POST', 'DELETE'])
def vercel_api_fallback():
    matched = request.headers.get('x-matched-path') or request.headers.get('x-forwarded-uri') or request.args.get('path', '')
    if 'email/detail' in matched:
        return get_email_detail()
    elif 'account' in matched:
        if request.method == 'POST':
            if 'test' in matched:
                return test_account_connection()
            return save_account()
        elif request.method == 'DELETE':
            acc_id = matched.rstrip('/').split('/')[-1]
            return delete_account(acc_id)
        return get_accounts()
    return get_emails()

if __name__ == '__main__':
    print("🚀 Menjalankan Dashboard Email di http://127.0.0.1:5000")
    print("📁 Menggunakan konfigurasi akun dari accounts.json")
    app.run(host='127.0.0.1', port=5000, debug=True)