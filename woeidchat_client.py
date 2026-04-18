"""
WoeidChat Client
CustomTkinter + WebSockets + RSA/AES E2E Encryption
Run: python woeidchat_client.py
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import asyncio
import websockets
import json
import requests
import os
import pickle
import queue
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import secrets

# ─── Configuration ────────────────────────────────────────────────────────────

SERVER = "http://localhost:8765"
WS_SERVER = "ws://localhost:8765"

# ─── Theme ────────────────────────────────────────────────────────────────────

COLORS = {
    "bg":          "#0d0b14",
    "sidebar_bg":  "#13101e",
    "card_bg":     "#1a1628",
    "input_bg":    "#211d30",
    "bubble_me":   "#5b3fd4",
    "bubble_me2":  "#7055e8",
    "bubble_them": "#1e1a2e",
    "accent":      "#7c5dfa",
    "accent_dim":  "#5b3fd4",
    "text":        "#f0edff",
    "text_dim":    "#9b92c8",
    "text_muted":  "#5a5278",
    "online":      "#4ade80",
    "offline":     "#6b6898",
    "border":      "#2a2440",
    "danger":      "#f87171",
    "warning":     "#fbbf24",
    "hover":       "#241f38",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ─── E2E Encryption ───────────────────────────────────────────────────────────

class E2EEncryption:
    def __init__(self):
        self.private_key = None
        self.public_key = None

    def generate_keys(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        self.public_key = self.private_key.public_key()

    def get_public_key_pem(self) -> str:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

    def save_keys(self, username: str):
        data = {
            "private": self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        }
        os.makedirs("woeidchat_keys", exist_ok=True)
        with open(f"woeidchat_keys/{username}.pkl", "wb") as f:
            pickle.dump(data, f)

    def load_keys(self, username: str) -> bool:
        path = f"woeidchat_keys/{username}.pkl"
        if not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.private_key = serialization.load_pem_private_key(
            data["private"], password=None, backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        return True

    def encrypt(self, message: str, recipient_pub_pem: str) -> tuple[str, str]:
        aes_key = secrets.token_bytes(32)
        iv = secrets.token_bytes(16)

        padded = message.encode("utf-8")
        pad_len = 16 - (len(padded) % 16)
        padded += bytes([pad_len] * pad_len)

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv),
                        backend=default_backend())
        enc = cipher.encryptor()
        enc_msg = enc.update(padded) + enc.finalize()
        enc_content = base64.b64encode(iv + enc_msg).decode()

        pub_key = serialization.load_pem_public_key(
            recipient_pub_pem.encode(), backend=default_backend())
        enc_key = pub_key.encrypt(
            aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(), label=None
            )
        )
        return enc_content, base64.b64encode(enc_key).decode()

    def decrypt(self, enc_content: str, enc_key_b64: str) -> str:
        try:
            aes_key = self.private_key.decrypt(
                base64.b64decode(enc_key_b64),
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(), label=None
                )
            )
            raw = base64.b64decode(enc_content)
            iv, enc_msg = raw[:16], raw[16:]
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(
                iv), backend=default_backend())
            dec = cipher.decryptor()
            padded = dec.update(enc_msg) + dec.finalize()
            return padded[: -padded[-1]].decode("utf-8")
        except Exception:
            return "⚠ [Decryption failed — key mismatch?]"


# ─── WebSocket Worker ─────────────────────────────────────────────────────────

class WSWorker:
    def __init__(self, url: str, inbox: queue.Queue):
        self.url = url
        self.inbox = inbox
        self._send_q: asyncio.Queue = None
        self._loop: asyncio.AbstractEventLoop = None
        self._ws = None
        self._running = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect())

    async def _connect(self):
        self._send_q = asyncio.Queue()
        try:
            async with websockets.connect(self.url, ping_interval=20, ping_timeout=10) as ws:
                self._ws = ws
                self.inbox.put({"type": "__connected__"})
                await asyncio.gather(self._recv(ws), self._send_loop(ws))
        except Exception as e:
            self.inbox.put({"type": "__error__", "detail": str(e)})

    async def _recv(self, ws):
        try:
            async for raw in ws:
                try:
                    self.inbox.put(json.loads(raw))
                except Exception:
                    pass
        except Exception:
            self.inbox.put({"type": "__disconnected__"})

    async def _send_loop(self, ws):
        while self._running:
            try:
                msg = await asyncio.wait_for(self._send_q.get(), timeout=1.0)
                await ws.send(json.dumps(msg))
            except asyncio.TimeoutError:
                pass
            except Exception:
                break

    def send(self, data: dict):
        if self._loop and self._send_q:
            asyncio.run_coroutine_threadsafe(
                self._send_q.put(data), self._loop)

    def stop(self):
        self._running = False


# ─── API Client ──────────────────────────────────────────────────────────────

class API:
    def __init__(self):
        self.token = None

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def register(self, username, password, pub_key):
        r = requests.post(f"{SERVER}/register", json={"username": username,
                          "password": password, "public_key": pub_key}, timeout=8)
        r.raise_for_status()
        return r.json()

    def login(self, username, password):
        r = requests.post(
            f"{SERVER}/login", json={"username": username, "password": password}, timeout=8)
        r.raise_for_status()
        data = r.json()
        self.token = data["token"]
        return data

    def get_users(self):
        r = requests.get(f"{SERVER}/users", headers=self._h(), timeout=8)
        r.raise_for_status()
        return r.json()

    def get_public_key(self, username):
        r = requests.get(f"{SERVER}/public-key/{username}",
                         headers=self._h(), timeout=8)
        r.raise_for_status()
        return r.json()["public_key"]

    def get_messages(self, other):
        r = requests.get(f"{SERVER}/messages/{other}",
                         headers=self._h(), timeout=8)
        r.raise_for_status()
        return r.json()["messages"]

    def logout(self):
        try:
            requests.post(f"{SERVER}/logout", headers=self._h(), timeout=4)
        except Exception:
            pass
        self.token = None


# ─── Tooltip ─────────────────────────────────────────────────────────────────

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        x, y, _, _ = self.widget.bbox("insert") if hasattr(
            self.widget, "bbox") else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tip, text=self.text, background="#2a2440", foreground="#f0edff",
                       relief="flat", padx=8, pady=4, font=("Segoe UI", 10))
        lbl.pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ─── Main App ─────────────────────────────────────────────────────────────────

class WoeidChat(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WoeidChat")
        self.geometry("420x600")
        self.minsize(380, 500)
        self.configure(fg_color=COLORS["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # State
        self.username = None
        self.token = None
        self.current_chat = None
        self.chat_messages: dict[str, list] = {}
        self.pub_key_cache: dict[str, str] = {}
        self.online_users: set = set()
        self.unread: dict[str, int] = {}
        self.ws_worker: WSWorker = None
        self.inbox = queue.Queue()
        self.encryption = E2EEncryption()
        self.api = API()
        self._contact_buttons: dict[str, ctk.CTkFrame] = {}

        # UI state
        self.main_frame = None
        self.sidebar_frame = None
        self.chat_frame = None

        self._build_auth_screen()
        self._poll_inbox()

    # ── Auth Screen ──────────────────────────────────────────────────────────

    def _build_auth_screen(self):
        self._clear_window()
        self.geometry("420x580")
        self.resizable(False, False)

        # Background gradient effect via canvas
        bg = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        bg.pack(fill="both", expand=True)

        # Logo area
        logo_frame = ctk.CTkFrame(bg, fg_color="transparent")
        logo_frame.pack(pady=(48, 8))

        # Logo icon
        ctk.CTkLabel(logo_frame, text="⬡", font=ctk.CTkFont("Segoe UI Symbol", 52),
                     text_color=COLORS["accent"]).pack()
        ctk.CTkLabel(logo_frame, text="WoeidChat", font=ctk.CTkFont("Segoe UI", 28, weight="bold"),
                     text_color=COLORS["text"]).pack(pady=(4, 0))
        ctk.CTkLabel(logo_frame, text="End-to-End Encrypted Messenger",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 0))

        # E2E badge
        badge = ctk.CTkFrame(logo_frame, fg_color="#1a1628", corner_radius=20)
        badge.pack(pady=(10, 0))
        ctk.CTkLabel(badge, text="🔒  AES-256 + RSA-2048 Encryption",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=COLORS["accent"]).pack(padx=14, pady=5)

        # Tab frame
        card = ctk.CTkFrame(bg, fg_color=COLORS["card_bg"], corner_radius=20)
        card.pack(padx=32, pady=16, fill="x")

        # Tab buttons
        tab_row = ctk.CTkFrame(
            card, fg_color=COLORS["sidebar_bg"], corner_radius=12)
        tab_row.pack(fill="x", padx=16, pady=(16, 0))

        self._auth_tab = tk.StringVar(value="login")

        def mk_tab(text, val):
            def sel():
                self._auth_tab.set(val)
                _refresh_tabs()
            btn = ctk.CTkButton(tab_row, text=text, corner_radius=10, height=36,
                                font=ctk.CTkFont(
                                    "Segoe UI", 13, weight="bold"),
                                fg_color="transparent", hover_color=COLORS["hover"],
                                text_color=COLORS["text_dim"], command=sel)
            btn.pack(side="left", expand=True, fill="x", padx=4, pady=4)
            return btn

        tab_login = mk_tab("Sign In", "login")
        tab_reg = mk_tab("Register", "register")

        def _refresh_tabs():
            v = self._auth_tab.get()
            tab_login.configure(
                fg_color=COLORS["accent"] if v == "login" else "transparent",
                text_color=COLORS["text"] if v == "login" else COLORS["text_dim"]
            )
            tab_reg.configure(
                fg_color=COLORS["accent"] if v == "register" else "transparent",
                text_color=COLORS["text"] if v == "register" else COLORS["text_dim"]
            )
            login_section.pack_forget()
            reg_section.pack_forget()
            if v == "login":
                login_section.pack(fill="x", padx=16, pady=8)
            else:
                reg_section.pack(fill="x", padx=16, pady=8)

        # ── Login fields
        login_section = ctk.CTkFrame(card, fg_color="transparent")

        ctk.CTkLabel(login_section, text="Username", font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_dim"], anchor="w").pack(fill="x", pady=(8, 2))
        self.login_user = ctk.CTkEntry(login_section, height=42, corner_radius=12,
                                       fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                                       border_width=1, font=ctk.CTkFont("Segoe UI", 13),
                                       text_color=COLORS["text"], placeholder_text="Enter username")
        self.login_user.pack(fill="x")

        ctk.CTkLabel(login_section, text="Password", font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_dim"], anchor="w").pack(fill="x", pady=(10, 2))
        self.login_pass = ctk.CTkEntry(login_section, height=42, corner_radius=12,
                                       fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                                       border_width=1, font=ctk.CTkFont("Segoe UI", 13),
                                       text_color=COLORS["text"], show="•",
                                       placeholder_text="Enter password")
        self.login_pass.pack(fill="x")

        self.login_err = ctk.CTkLabel(login_section, text="", font=ctk.CTkFont("Segoe UI", 11),
                                      text_color=COLORS["danger"])
        self.login_err.pack(pady=(4, 0))

        self.login_btn = ctk.CTkButton(login_section, text="Sign In →", height=44, corner_radius=12,
                                       fg_color=COLORS["accent"], hover_color=COLORS["accent_dim"],
                                       font=ctk.CTkFont(
                                           "Segoe UI", 14, weight="bold"),
                                       text_color="white", command=self._do_login)
        self.login_btn.pack(fill="x", pady=(8, 16))
        self.login_pass.bind("<Return>", lambda _: self._do_login())

        # ── Register fields
        reg_section = ctk.CTkFrame(card, fg_color="transparent")

        ctk.CTkLabel(reg_section, text="Username", font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_dim"], anchor="w").pack(fill="x", pady=(8, 2))
        self.reg_user = ctk.CTkEntry(reg_section, height=42, corner_radius=12,
                                     fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                                     border_width=1, font=ctk.CTkFont("Segoe UI", 13),
                                     text_color=COLORS["text"], placeholder_text="3+ alphanumeric chars")
        self.reg_user.pack(fill="x")

        ctk.CTkLabel(reg_section, text="Password", font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_dim"], anchor="w").pack(fill="x", pady=(10, 2))
        self.reg_pass = ctk.CTkEntry(reg_section, height=42, corner_radius=12,
                                     fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                                     border_width=1, font=ctk.CTkFont("Segoe UI", 13),
                                     text_color=COLORS["text"], show="•",
                                     placeholder_text="6+ characters")
        self.reg_pass.pack(fill="x")

        ctk.CTkLabel(reg_section, text="Confirm Password", font=ctk.CTkFont("Segoe UI", 12),
                     text_color=COLORS["text_dim"], anchor="w").pack(fill="x", pady=(10, 2))
        self.reg_conf = ctk.CTkEntry(reg_section, height=42, corner_radius=12,
                                     fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                                     border_width=1, font=ctk.CTkFont("Segoe UI", 13),
                                     text_color=COLORS["text"], show="•",
                                     placeholder_text="Repeat password")
        self.reg_conf.pack(fill="x")

        self.reg_err = ctk.CTkLabel(reg_section, text="", font=ctk.CTkFont("Segoe UI", 11),
                                    text_color=COLORS["danger"])
        self.reg_err.pack(pady=(4, 0))

        self.reg_btn = ctk.CTkButton(reg_section, text="Create Account →", height=44, corner_radius=12,
                                     fg_color=COLORS["accent"], hover_color=COLORS["accent_dim"],
                                     font=ctk.CTkFont(
                                         "Segoe UI", 14, weight="bold"),
                                     text_color="white", command=self._do_register)
        self.reg_btn.pack(fill="x", pady=(8, 16))
        self.reg_conf.bind("<Return>", lambda _: self._do_register())

        _refresh_tabs()

        # Footer
        ctk.CTkLabel(bg, text="Messages are encrypted. Only you and your recipient can read them.",
                     font=ctk.CTkFont("Segoe UI", 10), text_color=COLORS["text_muted"],
                     wraplength=340).pack(pady=(0, 16))

    def _do_login(self):
        u = self.login_user.get().strip()
        p = self.login_pass.get()
        if not u or not p:
            self.login_err.configure(text="Please fill in all fields.")
            return
        self.login_btn.configure(state="disabled", text="Signing in...")
        self.login_err.configure(text="")

        def task():
            try:
                data = self.api.login(u, p)
                self.username = data["username"]
                self.token = data["token"]
                self.after(0, lambda: self._post_auth(is_new=False))
            except requests.HTTPError as e:
                msg = "Invalid credentials."
                try:
                    msg = e.response.json().get("detail", msg)
                except Exception:
                    pass
                self.after(0, lambda: (
                    self.login_err.configure(text=msg),
                    self.login_btn.configure(state="normal", text="Sign In →")
                ))
            except Exception as e:
                self.after(0, lambda: (
                    self.login_err.configure(
                        text=f"Cannot connect to server."),
                    self.login_btn.configure(state="normal", text="Sign In →")
                ))

        threading.Thread(target=task, daemon=True).start()

    def _do_register(self):
        u = self.reg_user.get().strip()
        p = self.reg_pass.get()
        c = self.reg_conf.get()
        if not u or not p or not c:
            self.reg_err.configure(text="Please fill in all fields.")
            return
        if p != c:
            self.reg_err.configure(text="Passwords do not match.")
            return
        self.reg_btn.configure(state="disabled", text="Creating account...")
        self.reg_err.configure(text="")

        def task():
            try:
                enc = E2EEncryption()
                if not enc.load_keys(u):
                    enc.generate_keys()
                    enc.save_keys(u)
                self.api.register(u, p, enc.get_public_key_pem())
                data = self.api.login(u, p)
                self.username = data["username"]
                self.token = data["token"]
                self.encryption = enc
                self.after(0, lambda: self._post_auth(is_new=True))
            except requests.HTTPError as e:
                msg = "Registration failed."
                try:
                    msg = e.response.json().get("detail", msg)
                except Exception:
                    pass
                self.after(0, lambda: (
                    self.reg_err.configure(text=msg),
                    self.reg_btn.configure(
                        state="normal", text="Create Account →")
                ))
            except Exception:
                self.after(0, lambda: (
                    self.reg_err.configure(text="Cannot connect to server."),
                    self.reg_btn.configure(
                        state="normal", text="Create Account →")
                ))

        threading.Thread(target=task, daemon=True).start()

    def _post_auth(self, is_new=False):
        if not is_new:
            if not self.encryption.load_keys(self.username):
                self.encryption.generate_keys()
                self.encryption.save_keys(self.username)
        self.api.token = self.token
        self._build_main_screen()
        self._start_websocket()

    # ── Main Screen ──────────────────────────────────────────────────────────

    def _build_main_screen(self):
        self._clear_window()
        self.geometry("980x680")
        self.minsize(780, 540)
        self.resizable(True, True)

        root = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        self._build_sidebar(root)
        self._build_chat_area(root)
        self._refresh_user_list()

    def _build_sidebar(self, parent):
        sb = ctk.CTkFrame(
            parent, fg_color=COLORS["sidebar_bg"], corner_radius=0, width=280)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(2, weight=1)
        self.sidebar_frame = sb

        # Header
        hdr = ctk.CTkFrame(sb, fg_color="transparent", height=70)
        hdr.pack(fill="x", padx=0, pady=0)
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="⬡ WoeidChat",
                     font=ctk.CTkFont("Segoe UI", 18, weight="bold"),
                     text_color=COLORS["accent"]).pack(side="left", padx=18, pady=18)

        # Current user info
        user_row = ctk.CTkFrame(
            sb, fg_color=COLORS["card_bg"], corner_radius=12)
        user_row.pack(fill="x", padx=12, pady=(0, 8))

        av_frame = ctk.CTkFrame(user_row, fg_color=COLORS["accent"], width=38, height=38,
                                corner_radius=19)
        av_frame.pack(side="left", padx=(10, 6), pady=8)
        av_frame.pack_propagate(False)
        ctk.CTkLabel(av_frame, text=self.username[0].upper(),
                     font=ctk.CTkFont("Segoe UI", 16, weight="bold"),
                     text_color="white").pack(expand=True)

        u_info = ctk.CTkFrame(user_row, fg_color="transparent")
        u_info.pack(side="left", fill="y", pady=6)
        ctk.CTkLabel(u_info, text=self.username,
                     font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
                     text_color=COLORS["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(u_info, text="🟢 Online",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=COLORS["online"]).pack(anchor="w")

        logout_btn = ctk.CTkButton(user_row, text="↩", width=32, height=32, corner_radius=8,
                                   fg_color="transparent", hover_color=COLORS["hover"],
                                   text_color=COLORS["text_muted"],
                                   font=ctk.CTkFont("Segoe UI", 16),
                                   command=self._logout)
        logout_btn.pack(side="right", padx=8)
        Tooltip(logout_btn, "Sign out")

        # Search
        search_frame = ctk.CTkFrame(sb, fg_color="transparent")
        search_frame.pack(fill="x", padx=12, pady=(4, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *_: self._filter_contacts())
        search_entry = ctk.CTkEntry(search_frame, height=36, corner_radius=18,
                                    fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                                    border_width=1, font=ctk.CTkFont("Segoe UI", 12),
                                    text_color=COLORS["text"], placeholder_text="🔍  Search contacts...",
                                    textvariable=self.search_var)
        search_entry.pack(fill="x")

        # Divider label
        ctk.CTkLabel(sb, text="CONTACTS", font=ctk.CTkFont("Segoe UI", 10, weight="bold"),
                     text_color=COLORS["text_muted"], anchor="w").pack(fill="x", padx=18, pady=(4, 2))

        # Contacts list
        self.contacts_scroll = ctk.CTkScrollableFrame(sb, fg_color="transparent",
                                                      scrollbar_fg_color=COLORS["sidebar_bg"],
                                                      scrollbar_button_color=COLORS["border"],
                                                      scrollbar_button_hover_color=COLORS["accent_dim"])
        self.contacts_scroll.pack(
            fill="both", expand=True, padx=8, pady=(0, 8))

        # Refresh button
        refresh_btn = ctk.CTkButton(sb, text="↻ Refresh Contacts", height=34, corner_radius=8,
                                    fg_color="transparent", hover_color=COLORS["hover"],
                                    border_color=COLORS["border"], border_width=1,
                                    font=ctk.CTkFont("Segoe UI", 11),
                                    text_color=COLORS["text_dim"],
                                    command=self._refresh_user_list)
        refresh_btn.pack(fill="x", padx=12, pady=(0, 12))

        # Lock badge
        lock_frame = ctk.CTkFrame(
            sb, fg_color=COLORS["card_bg"], corner_radius=10)
        lock_frame.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(lock_frame, text="🔒  End-to-End Encrypted",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=COLORS["text_muted"]).pack(pady=6)

    def _build_chat_area(self, parent):
        chat_root = ctk.CTkFrame(
            parent, fg_color=COLORS["bg"], corner_radius=0)
        chat_root.grid(row=0, column=1, sticky="nsew")
        chat_root.grid_rowconfigure(1, weight=1)
        chat_root.grid_columnconfigure(0, weight=1)
        self.chat_frame = chat_root

        # Empty state
        self.empty_state = ctk.CTkFrame(chat_root, fg_color="transparent")
        self.empty_state.grid(row=0, column=0, rowspan=3, sticky="nsew")
        ctk.CTkLabel(self.empty_state, text="⬡", font=ctk.CTkFont("Segoe UI Symbol", 64),
                     text_color=COLORS["border"]).pack(expand=True, pady=(160, 8))
        ctk.CTkLabel(self.empty_state, text="Select a contact to start chatting",
                     font=ctk.CTkFont("Segoe UI", 15), text_color=COLORS["text_muted"]).pack()
        ctk.CTkLabel(self.empty_state, text="All messages are end-to-end encrypted",
                     font=ctk.CTkFont("Segoe UI", 11), text_color=COLORS["text_muted"]).pack(pady=(4, 0))

        # Chat header (hidden until contact selected)
        self.chat_header = ctk.CTkFrame(chat_root, fg_color=COLORS["sidebar_bg"],
                                        corner_radius=0, height=65)
        self.chat_header.grid_columnconfigure(1, weight=1)
        self.chat_av = None
        self.chat_name_lbl = None
        self.chat_status_lbl = None

        # Messages area
        self.messages_outer = ctk.CTkFrame(
            chat_root, fg_color=COLORS["bg"], corner_radius=0)
        self.messages_scroll = ctk.CTkScrollableFrame(self.messages_outer, fg_color=COLORS["bg"],
                                                      scrollbar_fg_color=COLORS["bg"],
                                                      scrollbar_button_color=COLORS["border"],
                                                      scrollbar_button_hover_color=COLORS["accent_dim"])
        self.messages_scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # Input area
        self.input_frame = ctk.CTkFrame(chat_root, fg_color=COLORS["sidebar_bg"],
                                        corner_radius=0, height=72)
        self.input_frame.pack_propagate(False)

        inp_inner = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        inp_inner.pack(fill="both", expand=True, padx=16, pady=12)

        self.msg_input = ctk.CTkEntry(inp_inner, height=46, corner_radius=23,
                                      fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                                      border_width=1, font=ctk.CTkFont("Segoe UI", 13),
                                      text_color=COLORS["text"],
                                      placeholder_text="Type a message...")
        self.msg_input.pack(side="left", fill="x", expand=True)
        self.msg_input.bind("<Return>", lambda _: self._send_message())

        self.send_btn = ctk.CTkButton(inp_inner, text="➤", width=46, height=46,
                                      corner_radius=23, fg_color=COLORS["accent"],
                                      hover_color=COLORS["accent_dim"],
                                      font=ctk.CTkFont("Segoe UI", 18),
                                      text_color="white", command=self._send_message)
        self.send_btn.pack(side="right", padx=(10, 0))

    def _show_chat_ui(self):
        self.empty_state.grid_remove()

        self.chat_header.grid(row=0, column=0, sticky="ew")
        self.messages_outer.grid(row=1, column=0, sticky="nsew")
        self.messages_outer.grid_rowconfigure(0, weight=1)
        self.messages_outer.grid_columnconfigure(0, weight=1)
        self.input_frame.grid(row=2, column=0, sticky="ew")

        # Build header contents if not already
        if self.chat_name_lbl is None:
            av = ctk.CTkFrame(self.chat_header, fg_color=COLORS["accent_dim"],
                              width=42, height=42, corner_radius=21)
            av.grid(row=0, column=0, padx=(16, 10), pady=12)
            av.grid_propagate(False)
            self.chat_av_lbl = ctk.CTkLabel(av, text="?",
                                            font=ctk.CTkFont(
                                                "Segoe UI", 18, weight="bold"),
                                            text_color="white")
            self.chat_av_lbl.pack(expand=True)

            info = ctk.CTkFrame(self.chat_header, fg_color="transparent")
            info.grid(row=0, column=1, sticky="w")
            self.chat_name_lbl = ctk.CTkLabel(info, text="",
                                              font=ctk.CTkFont(
                                                  "Segoe UI", 14, weight="bold"),
                                              text_color=COLORS["text"])
            self.chat_name_lbl.pack(anchor="w")
            self.chat_status_lbl = ctk.CTkLabel(info, text="",
                                                font=ctk.CTkFont(
                                                    "Segoe UI", 11),
                                                text_color=COLORS["text_muted"])
            self.chat_status_lbl.pack(anchor="w")

            lock_lbl = ctk.CTkLabel(self.chat_header, text="🔒 E2E",
                                    font=ctk.CTkFont("Segoe UI", 10),
                                    text_color=COLORS["accent"])
            lock_lbl.grid(row=0, column=2, padx=16)

        # Update header
        u = self.current_chat
        self.chat_av_lbl.configure(text=u[0].upper())
        self.chat_name_lbl.configure(text=u)
        status = "🟢 Online" if u in self.online_users else "⚫ Offline"
        self.chat_status_lbl.configure(text=status,
                                       text_color=COLORS["online"] if u in self.online_users else COLORS["text_muted"])

    def _select_contact(self, username: str):
        self.current_chat = username
        self.unread[username] = 0
        self._update_contact_ui(username)
        self._show_chat_ui()
        self._clear_messages()

        def load():
            try:
                msgs = self.api.get_messages(username)
                if username not in self.chat_messages:
                    self.chat_messages[username] = []
                existing_ts = {m["timestamp"]
                               for m in self.chat_messages[username]}
                for m in msgs:
                    if m["timestamp"] not in existing_ts:
                        if m["sender"] != self.username:
                            m["_decrypted"] = self.encryption.decrypt(
                                m["encrypted_content"], m["encrypted_key"]
                            )
                        self.chat_messages[username].append(m)
                self.after(0, lambda: self._render_messages(username))
            except Exception:
                pass

        threading.Thread(target=load, daemon=True).start()

    def _render_messages(self, username: str):
        if self.current_chat != username:
            return
        self._clear_messages()
        for m in self.chat_messages.get(username, []):
            is_mine = m["sender"] == self.username
            text = m.get("_decrypted", m.get("_text", ""))
            if not text:
                continue
            ts = m.get("timestamp", "")
            self._add_bubble(text, is_mine, ts)
        self.after(50, self._scroll_bottom)

    def _clear_messages(self):
        for widget in self.messages_scroll.winfo_children():
            widget.destroy()

    def _add_bubble(self, text: str, is_mine: bool, timestamp: str = ""):
        # Format timestamp
        ts_display = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                ts_display = dt.strftime("%H:%M")
            except Exception:
                ts_display = ""

        outer = ctk.CTkFrame(self.messages_scroll, fg_color="transparent")
        outer.pack(fill="x", pady=2, padx=8)

        bubble = ctk.CTkFrame(outer,
                              fg_color=COLORS["bubble_me"] if is_mine else COLORS["bubble_them"],
                              corner_radius=18)

        msg_lbl = ctk.CTkLabel(bubble, text=text,
                               font=ctk.CTkFont("Segoe UI", 13),
                               text_color=COLORS["text"],
                               wraplength=340, justify="left", anchor="w")
        msg_lbl.pack(padx=14, pady=(10, 4), anchor="w")

        if ts_display:
            ts_lbl = ctk.CTkLabel(bubble, text=ts_display,
                                  font=ctk.CTkFont("Segoe UI", 9),
                                  text_color="#c8c0e8" if is_mine else COLORS["text_muted"])
            ts_lbl.pack(padx=14, pady=(0, 7), anchor="e")

        if is_mine:
            bubble.pack(side="right", anchor="e")
        else:
            bubble.pack(side="left", anchor="w")

    def _scroll_bottom(self):
        try:
            self.messages_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _send_message(self):
        text = self.msg_input.get().strip()
        if not text or not self.current_chat:
            return
        self.msg_input.delete(0, "end")
        recipient = self.current_chat

        def send():
            try:
                if recipient not in self.pub_key_cache:
                    pk = self.api.get_public_key(recipient)
                    self.pub_key_cache[recipient] = pk
                pub_key = self.pub_key_cache[recipient]
                enc_content, enc_key = self.encryption.encrypt(text, pub_key)

                self.ws_worker.send({
                    "type": "message",
                    "recipient": recipient,
                    "encrypted_content": enc_content,
                    "encrypted_key": enc_key
                })

                # Store locally
                ts = datetime.utcnow().isoformat()
                msg_obj = {
                    "sender": self.username,
                    "recipient": recipient,
                    "encrypted_content": enc_content,
                    "encrypted_key": enc_key,
                    "timestamp": ts,
                    "_text": text
                }
                if recipient not in self.chat_messages:
                    self.chat_messages[recipient] = []
                self.chat_messages[recipient].append(msg_obj)

                self.after(0, lambda: self._add_bubble(text, True, ts))
                self.after(50, self._scroll_bottom)

            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Send Error", str(e)))

        threading.Thread(target=send, daemon=True).start()

    # ── Contacts ─────────────────────────────────────────────────────────────

    def _refresh_user_list(self):
        def load():
            try:
                data = self.api.get_users()
                self.online_users = set(data.get("online", []))
                users = data.get("users", [])
                self.after(0, lambda: self._render_contact_list(users))
            except Exception:
                pass
        threading.Thread(target=load, daemon=True).start()

    def _render_contact_list(self, users: list):
        for w in self.contacts_scroll.winfo_children():
            w.destroy()
        self._contact_buttons = {}

        for u in sorted(users):
            self._add_contact_button(u)

    def _add_contact_button(self, username: str):
        is_online = username in self.online_users
        unread_count = self.unread.get(username, 0)

        card = ctk.CTkFrame(self.contacts_scroll, fg_color="transparent",
                            corner_radius=12, cursor="hand2")
        card.pack(fill="x", pady=2)
        card.bind("<Button-1>", lambda _: self._select_contact(username))

        inner = ctk.CTkFrame(card, fg_color=COLORS["card_bg"] if self.current_chat == username else "transparent",
                             corner_radius=12, cursor="hand2")
        inner.pack(fill="x")
        inner.bind("<Button-1>", lambda _: self._select_contact(username))

        def on_enter(_):
            if self.current_chat != username:
                inner.configure(fg_color=COLORS["hover"])

        def on_leave(_):
            if self.current_chat != username:
                inner.configure(fg_color="transparent")
        inner.bind("<Enter>", on_enter)
        inner.bind("<Leave>", on_leave)

        # Avatar
        av = ctk.CTkFrame(inner, fg_color=COLORS["accent_dim"] if is_online else COLORS["card_bg"],
                          width=40, height=40, corner_radius=20)
        av.pack(side="left", padx=(10, 8), pady=8)
        av.pack_propagate(False)
        av.bind("<Button-1>", lambda _: self._select_contact(username))
        ctk.CTkLabel(av, text=username[0].upper(),
                     font=ctk.CTkFont("Segoe UI", 15, weight="bold"),
                     text_color="white").pack(expand=True)

        # Online dot
        dot_color = COLORS["online"] if is_online else COLORS["offline"]
        dot = ctk.CTkFrame(inner, fg_color=dot_color,
                           width=10, height=10, corner_radius=5)
        dot.place(in_=av, relx=0.78, rely=0.78)

        # Info
        info_frame = ctk.CTkFrame(inner, fg_color="transparent")
        info_frame.pack(side="left", fill="y", pady=8)
        info_frame.bind("<Button-1>", lambda _: self._select_contact(username))

        ctk.CTkLabel(info_frame, text=username,
                     font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
                     text_color=COLORS["text"], anchor="w").pack(anchor="w")
        status_text = "Online" if is_online else "Offline"
        ctk.CTkLabel(info_frame, text=status_text,
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=COLORS["online"] if is_online else COLORS["text_muted"]).pack(anchor="w")

        # Unread badge
        if unread_count > 0:
            badge_f = ctk.CTkFrame(inner, fg_color=COLORS["accent"], corner_radius=10,
                                   width=22, height=22)
            badge_f.pack(side="right", padx=10)
            badge_f.pack_propagate(False)
            ctk.CTkLabel(badge_f, text=str(unread_count) if unread_count < 10 else "9+",
                         font=ctk.CTkFont("Segoe UI", 10, weight="bold"),
                         text_color="white").pack(expand=True)

        self._contact_buttons[username] = (inner, av, dot)

    def _update_contact_ui(self, username: str):
        # Re-render contacts to update selection / badges
        self._refresh_user_list()

    def _filter_contacts(self):
        q = self.search_var.get().lower().strip()
        for u, (card, av, dot) in self._contact_buttons.items():
            if q in u.lower():
                card.pack(fill="x")
            else:
                card.pack_forget()

    # ── WebSocket & Inbox ─────────────────────────────────────────────────────

    def _start_websocket(self):
        url = f"{WS_SERVER}/ws/{self.token}"
        self.ws_worker = WSWorker(url, self.inbox)
        self.ws_worker.start()

    def _poll_inbox(self):
        try:
            while True:
                msg = self.inbox.get_nowait()
                self._handle_inbox(msg)
        except queue.Empty:
            pass
        self.after(30, self._poll_inbox)

    def _handle_inbox(self, msg: dict):
        t = msg.get("type")

        if t == "__connected__":
            self._refresh_user_list()

        elif t == "message":
            sender = msg["sender"]
            enc_content = msg["encrypted_content"]
            enc_key = msg["encrypted_key"]
            timestamp = msg.get("timestamp", "")
            text = self.encryption.decrypt(enc_content, enc_key)

            m_obj = {
                "sender": sender,
                "recipient": self.username,
                "encrypted_content": enc_content,
                "encrypted_key": enc_key,
                "timestamp": timestamp,
                "_decrypted": text
            }
            if sender not in self.chat_messages:
                self.chat_messages[sender] = []
            self.chat_messages[sender].append(m_obj)

            if self.current_chat == sender:
                self._add_bubble(text, False, timestamp)
                self._scroll_bottom()
            else:
                self.unread[sender] = self.unread.get(sender, 0) + 1
                self._refresh_user_list()

        elif t == "presence":
            uname = msg.get("username")
            status = msg.get("status")
            if status == "online":
                self.online_users.add(uname)
            else:
                self.online_users.discard(uname)
            self._refresh_user_list()
            if self.current_chat == uname and self.chat_status_lbl:
                s = "🟢 Online" if uname in self.online_users else "⚫ Offline"
                color = COLORS["online"] if uname in self.online_users else COLORS["text_muted"]
                self.chat_status_lbl.configure(text=s, text_color=color)

        elif t == "ack":
            pass

        elif t == "__error__":
            pass

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _clear_window(self):
        for w in self.winfo_children():
            w.destroy()

    def _logout(self):
        if messagebox.askyesno("Sign Out", "Are you sure you want to sign out?"):
            if self.ws_worker:
                self.ws_worker.stop()
            threading.Thread(target=self.api.logout, daemon=True).start()
            self.username = None
            self.token = None
            self.current_chat = None
            self.chat_messages = {}
            self.online_users = set()
            self.encryption = E2EEncryption()
            self._build_auth_screen()

    def _on_close(self):
        if self.ws_worker:
            self.ws_worker.stop()
        if self.token:
            threading.Thread(target=self.api.logout, daemon=True).start()
        self.destroy()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═"*50)
    print("  🔐 WoeidChat Client")
    print("  Connecting to localhost:8765")
    print("═"*50 + "\n")
    app = WoeidChat()
    app.mainloop()
