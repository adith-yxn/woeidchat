"""
WoeidChat Diagnostic — run this to find what's broken
python diagnose.py
"""
import socket
import sys
import subprocess

OK = "✅"
FAIL = "❌"
WARN = "⚠️"

print("\n" + "═"*52)
print("  WoeidChat Diagnostic")
print("═"*52)

# Python version
v = sys.version_info
print(f"\n{'Python version':30} {v.major}.{v.minor}.{v.micro}")
if v.major < 3 or (v.major == 3 and v.minor < 10):
    print(f"  {FAIL} Need Python 3.10+. You have {v.major}.{v.minor}")
    print("     Download: https://www.python.org/downloads/")
else:
    print(f"  {OK} Python version OK")

# Check each package
packages = [
    ("fastapi",       "pip install fastapi"),
    ("uvicorn",       "pip install uvicorn[standard]"),
    ("websockets",    "pip install websockets"),
    ("customtkinter", "pip install customtkinter"),
    ("cryptography",  "pip install cryptography"),
    ("requests",      "pip install requests"),
    ("pydantic",      "pip install pydantic"),
]

print(f"\n{'Package checks':}")
missing = []
for pkg, install_cmd in packages:
    try:
        mod = __import__(pkg)
        ver = getattr(mod, "__version__", "?")
        print(f"  {OK} {pkg:<20} v{ver}")
    except ImportError:
        print(f"  {FAIL} {pkg:<20} NOT INSTALLED  →  {install_cmd}")
        missing.append(install_cmd)

# Check tkinter (built-in but sometimes missing on Linux)
print()
try:
    import tkinter
    tkinter.Tk().destroy()
    print(f"  {OK} tkinter               working")
except Exception as e:
    print(f"  {FAIL} tkinter               BROKEN: {e}")
    missing.append("# On Ubuntu/Debian: sudo apt install python3-tk")
    missing.append("# On Fedora: sudo dnf install python3-tkinter")

# Check port
print()
try:
    s = socket.socket()
    s.settimeout(1)
    result = s.connect_ex(("localhost", 8765))
    s.close()
    if result == 0:
        print(
            f"  {WARN} Port 8765             ALREADY IN USE (server may already be running)")
    else:
        print(f"  {OK} Port 8765             available")
except Exception:
    print(f"  {OK} Port 8765             available")

# Summary
print("\n" + "─"*52)
if missing:
    print(f"\n{FAIL} FIX THESE ISSUES:\n")
    for cmd in missing:
        print(f"   {cmd}")
    print(f"\n  Then re-run: python woeidchat_server.py")
    print(f"  In another terminal: python woeidchat_client.py\n")
else:
    print(f"\n{OK} Everything looks good!")
    print(f"\n  Run in TWO separate terminals:")
    print(f"    Terminal 1:  python woeidchat_server.py")
    print(f"    Terminal 2:  python woeidchat_client.py")
    print(f"\n  To test with 2 users, open a 3rd terminal:")
    print(f"    Terminal 3:  python woeidchat_client.py\n")
print("═"*52 + "\n")
