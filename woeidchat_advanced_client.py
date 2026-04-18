"""
WoeidChat Advanced Client - Full Featured Python GUI
Features: User Discovery, Groups, Profiles, Search, Follow System, E2E Encryption
Run: python woeidchat_advanced_client.py
"""

import customtkinter as ctk
from customtkinter import CTkToplevel, CTkButton, CTkLabel, CTkEntry, CTkTextbox, CTkFrame, CTkScrollableFrame
import asyncio
import websockets
import json
import threading
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import requests
import base64
import secrets

# ─── Configuration ───────────────────────────────────────────────────────

API_URL = "http://localhost:8765"
WS_URL = "ws://localhost:8765"
COLORS = {
    "bg": "#0a0a0a",
    "fg": "#ffffff",
    "accent": "#00d4ff",
    "accent_dark": "#0099cc",
    "secondary": "#1a1a1a",
    "online": "#00ff00",
    "offline": "#808080"
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ─── Encryption ──────────────────────────────────────────────────────────

class E2EEncryption:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.load_or_generate_keys()
    
    def load_or_generate_keys(self):
        keys_dir = Path("woeidchat_keys")
        keys_dir.mkdir(exist_ok=True)
        
        private_key_path = keys_dir / "private.pem"
        public_key_path = keys_dir / "public.pem"
        
        if private_key_path.exists() and public_key_path.exists():
            with open(private_key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            with open(public_key_path, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(), backend=default_backend()
                )
        else:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
            
            with open(private_key_path, "wb") as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            with open(public_key_path, "wb") as f:
                f.write(self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
    
    def get_public_key_pem(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
    
    def encrypt_message(self, message: str, recipient_public_key_pem: str) -> tuple:
        """Encrypt message with AES-256, then encrypt key with RSA"""
        public_key = serialization.load_pem_public_key(
            recipient_public_key_pem.encode(), backend=default_backend()
        )
        
        # Generate AES key and IV
        aes_key = secrets.token_bytes(32)  # 256-bit key
        iv = secrets.token_bytes(16)
        
        # Encrypt message with AES
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Add PKCS7 padding
        plaintext = message.encode()
        padding_length = 16 - (len(plaintext) % 16)
        plaintext += bytes([padding_length] * padding_length)
        
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # Encrypt AES key with RSA
        encrypted_key = public_key.encrypt(
            aes_key + iv,
            padding.OAEP(hashes.SHA256(), hashes.SHA256(), None)
        )
        
        return base64.b64encode(ciphertext).decode(), base64.b64encode(encrypted_key).decode()
    
    def decrypt_message(self, encrypted_content: str, encrypted_key: str) -> str:
        """Decrypt message encrypted with AES, using RSA-decrypted key"""
        try:
            # Decrypt AES key with RSA private key
            encrypted_key_bytes = base64.b64decode(encrypted_key)
            key_and_iv = self.private_key.decrypt(
                encrypted_key_bytes,
                padding.OAEP(hashes.SHA256(), hashes.SHA256(), None)
            )
            
            aes_key = key_and_iv[:32]
            iv = key_and_iv[32:48]
            
            # Decrypt message with AES
            ciphertext = base64.b64decode(encrypted_content)
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            padding_length = plaintext[-1]
            plaintext = plaintext[:-padding_length]
            
            return plaintext.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return "[Failed to decrypt message]"


# ─── WebSocket Worker ────────────────────────────────────────────────────

class WSWorker(threading.Thread):
    def __init__(self, token, on_message_callback):
        super().__init__(daemon=True)
        self.token = token
        self.on_message = on_message_callback
        self.websocket = None
        self.loop = None
        self.running = True
    
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._ws_connect())
    
    async def _ws_connect(self):
        try:
            async with websockets.connect(f"{WS_URL}/ws/{self.token}") as websocket:
                self.websocket = websocket
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        self.on_message(data)
                    except asyncio.TimeoutError:
                        await websocket.send(json.dumps({"type": "ping"}))
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    def send_message(self, data):
        if self.loop and self.running:
            asyncio.run_coroutine_threadsafe(self._send(data), self.loop)
    
    async def _send(self, data):
        if self.websocket:
            await self.websocket.send(json.dumps(data))
    
    def stop(self):
        self.running = False


# ─── API Client ──────────────────────────────────────────────────────────

class API:
    def __init__(self, token=None):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    def set_token(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def register(self, username, password, password_hint, public_key):
        return requests.post(f"{API_URL}/register", json={
            "username": username,
            "password": password,
            "password_hint": password_hint,
            "public_key": public_key
        }).json()
    
    def login(self, username, password):
        return requests.post(f"{API_URL}/login", json={
            "username": username,
            "password": password
        }).json()
    
    def get_password_hint(self, username):
        return requests.get(f"{API_URL}/forgot-password?username={username}").json()
    
    def search_users(self, query):
        return requests.get(f"{API_URL}/search-users?query={query}", headers=self.headers).json()
    
    def get_user_profile(self, username):
        return requests.get(f"{API_URL}/user/{username}", headers=self.headers).json()
    
    def update_profile(self, bio, status_message, avatar_url):
        return requests.post(f"{API_URL}/profile", json={
            "bio": bio,
            "status_message": status_message,
            "avatar_url": avatar_url
        }, headers=self.headers).json()
    
    def follow_user(self, username):
        return requests.post(f"{API_URL}/follow/{username}", headers=self.headers).json()
    
    def create_group(self, group_name, description, is_public):
        return requests.post(f"{API_URL}/groups/create", json={
            "group_name": group_name,
            "description": description,
            "is_public": is_public
        }, headers=self.headers).json()
    
    def list_groups(self):
        return requests.get(f"{API_URL}/groups", headers=self.headers).json()
    
    def join_group(self, group_id):
        return requests.post(f"{API_URL}/groups/{group_id}/join", headers=self.headers).json()
    
    def list_group_members(self, group_id):
        return requests.get(f"{API_URL}/groups/{group_id}/members", headers=self.headers).json()


# ─── Main Application ────────────────────────────────────────────────────

class WoeidChatAdvanced(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WoeidChat Advanced - v2.0")
        self.geometry("1000x700")
        self.resizable(True, True)
        
        self.encryption = E2EEncryption()
        self.api = API()
        self.ws_worker = None
        self.current_user = None
        self.current_chat = None
        self.current_group = None
        
        self._build_auth_screen()
    
    def _build_auth_screen(self):
        """Build login/register screen"""
        self.auth_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        self.auth_frame.pack(fill="both", expand=True)
        
        # Title
        title = ctk.CTkLabel(self.auth_frame, text="🔐 WoeidChat Advanced", 
                            font=("Arial", 28, "bold"), text_color=COLORS["accent"])
        title.pack(pady=20)
        
        # Tab view for login/register
        tab_view = ctk.CTkTabview(self.auth_frame, width=400, height=300)
        tab_view.pack(pady=20)
        tab_view.add("Login")
        tab_view.add("Register")
        tab_view.add("Forgot Password")
        
        # ─── Login Tab ───
        login_frame = tab_view.tab("Login")
        
        CTkLabel(login_frame, text="Username:", text_color=COLORS["fg"]).pack(pady=5)
        login_username = ctk.CTkEntry(login_frame, width=300, placeholder_text="Enter username")
        login_username.pack(pady=5)
        
        CTkLabel(login_frame, text="Password:", text_color=COLORS["fg"]).pack(pady=5)
        login_password = ctk.CTkEntry(login_frame, width=300, show="*", placeholder_text="Enter password")
        login_password.pack(pady=5)
        
        def do_login():
            username = login_username.get()
            password = login_password.get()
            
            if not username or not password:
                messagebox.showerror("Error", "Fill all fields")
                return
            
            try:
                resp = self.api.login(username, password)
                if resp.get("success"):
                    self.current_user = {
                        "user_id": resp["user_id"],
                        "username": resp["username"],
                        "public_key": resp["public_key"],
                        "token": resp["token"]
                    }
                    self.api.set_token(resp["token"])
                    self.auth_frame.destroy()
                    self._build_main_screen()
                else:
                    messagebox.showerror("Login Failed", resp.get("detail", "Unknown error"))
            except Exception as e:
                messagebox.showerror("Error", f"Connection failed: {str(e)}")
        
        ctk.CTkButton(login_frame, text="Login", command=do_login, width=300,
                     fg_color=COLORS["accent"], hover_color=COLORS["accent_dark"]).pack(pady=10)
        
        # ─── Register Tab ───
        register_frame = tab_view.tab("Register")
        
        CTkLabel(register_frame, text="Username:", text_color=COLORS["fg"]).pack(pady=5)
        reg_username = ctk.CTkEntry(register_frame, width=300, placeholder_text="3-30 chars, letters/numbers/_")
        reg_username.pack(pady=5)
        
        CTkLabel(register_frame, text="Password:", text_color=COLORS["fg"]).pack(pady=5)
        reg_password = ctk.CTkEntry(register_frame, width=300, show="*")
        reg_password.pack(pady=5)
        
        CTkLabel(register_frame, text="Password Hint:", text_color=COLORS["fg"]).pack(pady=5)
        reg_hint = ctk.CTkEntry(register_frame, width=300, placeholder_text="Hint for password recovery")
        reg_hint.pack(pady=5)
        
        def do_register():
            username = reg_username.get()
            password = reg_password.get()
            hint = reg_hint.get()
            
            if not all([username, password, hint]):
                messagebox.showerror("Error", "Fill all fields")
                return
            
            if len(username) < 3 or len(username) > 30:
                messagebox.showerror("Error", "Username must be 3-30 characters")
                return
            
            if len(password) < 6:
                messagebox.showerror("Error", "Password must be at least 6 characters")
                return
            
            try:
                resp = self.api.register(username, password, hint, self.encryption.get_public_key_pem())
                if resp.get("success"):
                    messagebox.showinfo("Success", "Registration successful! Please login")
                    reg_username.delete(0, tk.END)
                    reg_password.delete(0, tk.END)
                    reg_hint.delete(0, tk.END)
                else:
                    messagebox.showerror("Registration Failed", resp.get("detail", "Username taken"))
            except Exception as e:
                messagebox.showerror("Error", f"Registration failed: {str(e)}")
        
        ctk.CTkButton(register_frame, text="Register", command=do_register, width=300,
                     fg_color=COLORS["accent"], hover_color=COLORS["accent_dark"]).pack(pady=10)
        
        # ─── Forgot Password Tab ───
        forgot_frame = tab_view.tab("Forgot Password")
        
        CTkLabel(forgot_frame, text="Username:", text_color=COLORS["fg"]).pack(pady=5)
        forgot_username = ctk.CTkEntry(forgot_frame, width=300)
        forgot_username.pack(pady=5)
        
        def get_hint():
            username = forgot_username.get()
            if not username:
                messagebox.showerror("Error", "Enter username")
                return
            
            try:
                resp = self.api.get_password_hint(username)
                if resp.get("success"):
                    messagebox.showinfo("Password Hint", f"Hint: {resp['hint']}")
                else:
                    messagebox.showerror("Error", "User not found")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ctk.CTkButton(forgot_frame, text="Get Hint", command=get_hint, width=300,
                     fg_color=COLORS["accent"], hover_color=COLORS["accent_dark"]).pack(pady=10)
    
    def _build_main_screen(self):
        """Build main chat screen"""
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header = ctk.CTkFrame(main_frame, fg_color=COLORS["secondary"], height=60)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        username_label = ctk.CTkLabel(header, text=f"👤 {self.current_user['username']}", 
                                     font=("Arial", 14, "bold"), text_color=COLORS["accent"])
        username_label.pack(side="left", padx=20, pady=15)
        
        logout_btn = ctk.CTkButton(header, text="Logout", width=80, height=30,
                                  command=self._logout, fg_color=COLORS["accent"],
                                  hover_color=COLORS["accent_dark"])
        logout_btn.pack(side="right", padx=20, pady=15)
        
        # Main content with tabs
        tab_view = ctk.CTkTabview(main_frame)
        tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tabs
        tab_view.add("🔍 Discover Users")
        tab_view.add("👥 Groups")
        tab_view.add("💬 Chats")
        tab_view.add("👤 Profile")
        
        # ─── Discover Users Tab ───
        self._build_discover_tab(tab_view.tab("🔍 Discover Users"))
        
        # ─── Groups Tab ───
        self._build_groups_tab(tab_view.tab("👥 Groups"))
        
        # ─── Chats Tab ───
        self._build_chats_tab(tab_view.tab("💬 Chats"))
        
        # ─── Profile Tab ───
        self._build_profile_tab(tab_view.tab("👤 Profile"))
        
        # Start WebSocket
        self._start_websocket()
    
    def _build_discover_tab(self, parent):
        """Build user discovery interface"""
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Search
        search_frame = ctk.CTkFrame(frame, fg_color=COLORS["secondary"])
        search_frame.pack(fill="x", pady=10)
        
        CTkLabel(search_frame, text="Search Users:", text_color=COLORS["fg"]).pack(side="left", padx=10)
        search_entry = ctk.CTkEntry(search_frame, width=300, placeholder_text="Search by username...")
        search_entry.pack(side="left", padx=5)
        
        # Results frame
        results_frame = CTkScrollableFrame(frame, fg_color=COLORS["bg"])
        results_frame.pack(fill="both", expand=True, pady=10)
        
        def do_search():
            query = search_entry.get()
            if not query:
                return
            
            try:
                resp = self.api.search_users(query)
                for widget in results_frame.winfo_children():
                    widget.destroy()
                
                for user in resp.get("results", []):
                    user_card = ctk.CTkFrame(results_frame, fg_color=COLORS["secondary"], height=80)
                    user_card.pack(fill="x", pady=5, padx=5)
                    user_card.pack_propagate(False)
                    
                    CTkLabel(user_card, text=f"@{user['username']}", font=("Arial", 12, "bold"),
                            text_color=COLORS["accent"]).pack(anchor="w", padx=10, pady=3)
                    
                    status_text = "🟢 Online" if user['online_status'] else "⚫ Offline"
                    CTkLabel(user_card, text=f"{status_text} | {user['bio']}", text_color=COLORS["fg"]).pack(anchor="w", padx=10)
                    
                    action_frame = ctk.CTkFrame(user_card, fg_color=COLORS["secondary"])
                    action_frame.pack(anchor="e", padx=10, pady=5)
                    
                    def view_profile(u=user):
                        self._show_user_profile(u)
                    
                    def follow(u=user):
                        try:
                            resp = self.api.follow_user(u['username'])
                            messagebox.showinfo("Success", "Following user")
                        except Exception as e:
                            messagebox.showerror("Error", str(e))
                    
                    ctk.CTkButton(action_frame, text="View Profile", width=100,
                                 command=view_profile, fg_color=COLORS["accent"]).pack(side="left", padx=5)
                    ctk.CTkButton(action_frame, text="Follow", width=80,
                                 command=follow, fg_color=COLORS["accent"]).pack(side="left", padx=5)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        search_btn = ctk.CTkButton(search_frame, text="Search", width=100, command=do_search,
                                  fg_color=COLORS["accent"], hover_color=COLORS["accent_dark"])
        search_btn.pack(side="left", padx=5)
    
    def _build_groups_tab(self, parent):
        """Build groups interface"""
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        button_frame = ctk.CTkFrame(frame, fg_color=COLORS["bg"])
        button_frame.pack(fill="x", pady=10)
        
        def create_group_dialog():
            dialog = CTkToplevel(self)
            dialog.title("Create Group")
            dialog.geometry("400x300")
            dialog.configure(fg_color=COLORS["bg"])
            
            CTkLabel(dialog, text="Group Name:", text_color=COLORS["fg"]).pack(pady=5)
            name_entry = ctk.CTkEntry(dialog, width=350, placeholder_text="Enter group name (max 100 chars)")
            name_entry.pack(pady=5)
            
            CTkLabel(dialog, text="Description:", text_color=COLORS["fg"]).pack(pady=5)
            desc_entry = ctk.CTkTextbox(dialog, width=350, height=100)
            desc_entry.pack(pady=5)
            
            is_public_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(dialog, text="Public Group", variable=is_public_var,
                           text_color=COLORS["fg"]).pack(pady=5)
            
            def create():
                try:
                    name = name_entry.get()
                    desc = desc_entry.get("1.0", tk.END).strip()
                    
                    if not name:
                        messagebox.showerror("Error", "Enter group name")
                        return
                    
                    resp = self.api.create_group(name, desc, is_public_var.get())
                    if resp.get("success"):
                        messagebox.showinfo("Success", "Group created successfully")
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", "Failed to create group")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
            
            ctk.CTkButton(dialog, text="Create", command=create, width=350,
                         fg_color=COLORS["accent"]).pack(pady=10)
        
        ctk.CTkButton(button_frame, text="Create Group", command=create_group_dialog, width=150,
                     fg_color=COLORS["accent"], hover_color=COLORS["accent_dark"]).pack(side="left", padx=5)
        
        # Groups list
        groups_frame = CTkScrollableFrame(frame, fg_color=COLORS["bg"])
        groups_frame.pack(fill="both", expand=True, pady=10)
        
        def load_groups():
            try:
                resp = self.api.list_groups()
                for widget in groups_frame.winfo_children():
                    widget.destroy()
                
                for group in resp.get("groups", []):
                    group_card = ctk.CTkFrame(groups_frame, fg_color=COLORS["secondary"], height=100)
                    group_card.pack(fill="x", pady=5, padx=5)
                    group_card.pack_propagate(False)
                    
                    CTkLabel(group_card, text=group['group_name'], font=("Arial", 12, "bold"),
                            text_color=COLORS["accent"]).pack(anchor="w", padx=10, pady=3)
                    
                    CTkLabel(group_card, text=group['description'][:100],
                            text_color=COLORS["fg"]).pack(anchor="w", padx=10)
                    
                    CTkLabel(group_card, text=f"👥 {group['member_count']} members",
                            text_color=COLORS["fg"]).pack(anchor="w", padx=10)
                    
                    def join(g=group):
                        try:
                            resp = self.api.join_group(g['group_id'])
                            messagebox.showinfo("Success", resp.get("message", "Joined group"))
                            load_groups()
                        except Exception as e:
                            messagebox.showerror("Error", str(e))
                    
                    ctk.CTkButton(group_card, text="Join Group", width=150, command=join,
                                 fg_color=COLORS["accent"], hover_color=COLORS["accent_dark"]).pack(anchor="e", padx=10, pady=5)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        load_groups()
    
    def _build_chats_tab(self, parent):
        """Build chats interface"""
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        CTkLabel(frame, text="💬 Chat Feature Coming Soon", font=("Arial", 16),
                text_color=COLORS["accent"]).pack(pady=20)
        CTkLabel(frame, text="Send direct messages to discovered users",
                text_color=COLORS["fg"]).pack()
    
    def _build_profile_tab(self, parent):
        """Build profile editing interface"""
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        CTkLabel(frame, text=f"Profile: {self.current_user['username']}", font=("Arial", 14, "bold"),
                text_color=COLORS["accent"]).pack(pady=10)
        
        CTkLabel(frame, text="Bio:", text_color=COLORS["fg"]).pack(pady=5)
        bio_entry = ctk.CTkEntry(frame, width=400, placeholder_text="Your bio")
        bio_entry.pack(pady=5)
        
        CTkLabel(frame, text="Status Message:", text_color=COLORS["fg"]).pack(pady=5)
        status_entry = ctk.CTkEntry(frame, width=400, placeholder_text="Your status message")
        status_entry.pack(pady=5)
        
        CTkLabel(frame, text="Avatar URL:", text_color=COLORS["fg"]).pack(pady=5)
        avatar_entry = ctk.CTkEntry(frame, width=400, placeholder_text="https://...")
        avatar_entry.pack(pady=5)
        
        def save_profile():
            try:
                resp = self.api.update_profile(
                    bio_entry.get() or None,
                    status_entry.get() or None,
                    avatar_entry.get() or None
                )
                messagebox.showinfo("Success", "Profile updated")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ctk.CTkButton(frame, text="Save Profile", command=save_profile, width=200,
                     fg_color=COLORS["accent"], hover_color=COLORS["accent_dark"]).pack(pady=10)
    
    def _show_user_profile(self, user):
        """Show detailed user profile"""
        try:
            dialog = CTkToplevel(self)
            dialog.title(f"@{user['username']}")
            dialog.geometry("400x400")
            dialog.configure(fg_color=COLORS["bg"])
            
            CTkLabel(dialog, text=f"@{user['username']}", font=("Arial", 16, "bold"),
                    text_color=COLORS["accent"]).pack(pady=10)
            
            status = "🟢 Online" if user['online_status'] else "⚫ Offline"
            CTkLabel(dialog, text=status, text_color=COLORS["fg"]).pack()
            
            CTkLabel(dialog, text=user['bio'], text_color=COLORS["fg"]).pack(pady=5)
            
            CTkLabel(dialog, text=f"Status: {user['status_message']}", text_color=COLORS["fg"]).pack(pady=5)
            
            CTkLabel(dialog, text=f"👥 Followers: {user['follower_count']} | Following: {user.get('following_count', 0)}",
                    text_color=COLORS["fg"]).pack(pady=10)
            
            def follow():
                try:
                    resp = self.api.follow_user(user['username'])
                    messagebox.showinfo("Success", "Following user")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
            
            ctk.CTkButton(dialog, text="Follow", command=follow, width=350,
                         fg_color=COLORS["accent"]).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _start_websocket(self):
        """Start WebSocket connection"""
        def on_message(data):
            msg_type = data.get("type")
            
            if msg_type == "presence":
                print(f"{data['username']} is {data['status']}")
            elif msg_type == "message":
                print(f"New message from {data['sender_id']}")
            elif msg_type == "typing":
                print(f"Typing: {data['is_typing']}")
        
        self.ws_worker = WSWorker(self.current_user['token'], on_message)
        self.ws_worker.start()
    
    def _logout(self):
        """Logout and return to auth screen"""
        if self.ws_worker:
            self.ws_worker.stop()
        
        for widget in self.winfo_children():
            widget.destroy()
        
        self.current_user = None
        self._build_auth_screen()
    
    def on_closing(self):
        """Clean up on exit"""
        if self.ws_worker:
            self.ws_worker.stop()
        self.destroy()


# ─── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
    ════════════════════════════════════════════════════════════
      🔐 WoeidChat Advanced Client - v2.0
      Features: User Discovery, Groups, Profiles, Follow, E2E
    ════════════════════════════════════════════════════════════
    """)
    
    app = WoeidChatAdvanced()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
