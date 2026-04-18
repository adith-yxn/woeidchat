#!/bin/bash
# WoeidChat Quick Setup Script
# Run this to get started with WoeidChat immediately

set -e

echo "🔐 WoeidChat Setup Assistant"
echo "============================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    echo "❌ Python 3.10+ required"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

# Create directories
mkdir -p woeidchat_keys uploads

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Next steps:"
echo ""
echo "   Terminal 1 - Start Server:"
echo "   $ python woeidchat_server_enhanced.py"
echo ""
echo "   Terminal 2+ - Start Clients:"
echo "   $ python woeidchat_client_enhanced.py"
echo ""
echo "📝 Registration:"
echo "   • Username: 3+ alphanumeric characters"
echo "   • Password: 6+ characters"
echo ""
echo "💡 Tips:"
echo "   • Run multiple clients to test messaging"
echo "   • All messages are encrypted end-to-end"
echo "   • Check README.md for more features"
echo ""
