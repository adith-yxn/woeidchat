# 🚀 FREE Hosting Deployment Guide

Deploy WoeidChat for **FREE** using any of these platforms!

---

## 📋 Choose Your Platform

| Platform | Cost | Setup Time | Uptime | Recommendation |
|----------|------|-----------|--------|-----------------|
| **Railway** | Free tier | ⭐⭐⭐⭐⭐ 5 min | 99.5% | ⭐ BEST |
| **Render** | Free tier | ⭐⭐⭐⭐ 10 min | 99.9% | ✅ Great |
| **Fly.io** | Free tier | ⭐⭐⭐ 15 min | 99.95% | ✅ Good |
| **Heroku** | ⚠️ Paid only | N/A | N/A | ❌ Not free |

---

## 🎯 QUICK START: Railway (RECOMMENDED - 5 MINUTES)

### **Step 1: Create Railway Account**
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub / Google
3. Click "Create Project" → "Deploy from GitHub"

### **Step 2: Fork & Connect Repository**
1. Fork this repo: [woeidchat](https://github.com/yourusername/woeidchat)
2. In Railway, select your forked repo
3. Choose `main` branch
4. Click "Deploy"

### **Step 3: Configure Environment**
Railway auto-detects Python. It will:
- ✅ Install Python 3.14
- ✅ Run `pip install -r requirements.txt`
- ✅ Start the server

### **Step 4: Get Your URL**
```
Your app is live at: https://woeidchat-xxx.railway.app
```

**That's it! Your app is running!** 🎉

Visit: `https://woeidchat-xxx.railway.app/static/login.html`

---

## 💚 Render (Alternative - 10 MINUTES)

### **Step 1: Create Render Account**
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New +" → "Web Service"

### **Step 2: Connect Repository**
1. Select your GitHub repo
2. Choose `main` branch
3. Set environment to Python 3.9+

### **Step 3: Configure Build**
```
Build Command:
pip install -r requirements.txt

Start Command:
python woeidchat_premium_server.py
```

### **Step 4: Deploy**
Click "Create Web Service" and wait ~5 minutes.

Your app will be at: `https://woeidchat-xxxx.onrender.com`

---

## 🚀 Fly.io (Alternative - 15 MINUTES)

### **Step 1: Install Fly CLI**
```bash
# macOS
brew install flyctl

# Windows (download from fly.io)
# Or use: choco install flyctl
```

### **Step 2: Create Dockerfile**
Create `Dockerfile` in your project root:
```dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8765

CMD ["python", "woeidchat_premium_server.py"]
```

### **Step 3: Deploy**
```bash
flyctl auth signup
flyctl launch
# Follow prompts
# Enter app name: woeidchat
# Choose region close to you

# Deploy
flyctl deploy
```

Your app will be at: `https://woeidchat.fly.dev`

---

## 🌐 Docker Deployment (Any Cloud)

### **Step 1: Create Dockerfile** (already in step above)

### **Step 2: Build Docker Image**
```bash
docker build -t woeidchat:latest .
```

### **Step 3: Test Locally**
```bash
docker run -p 8765:8765 woeidchat:latest
```

Visit: `http://localhost:8765/static/login.html`

### **Step 4: Push to Docker Hub** (Optional)
```bash
# Create account at hub.docker.com
docker login

# Tag image
docker tag woeidchat:latest yourusername/woeidchat:latest

# Push
docker push yourusername/woeidchat:latest
```

---

## 🔧 Environment Variables

Before deploying, set these variables on your hosting platform:

```
STRIPE_SECRET_KEY=sk_test_xxxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
DATABASE_URL=sqlite:///woeidchat.db
MAX_USERS=10000
PORT=8765
```

### **How to set on each platform:**

**Railway:**
- Go to "Variables" tab
- Add each variable

**Render:**
- Go to "Environment" section
- Add each variable

**Fly.io:**
- Edit `fly.toml` file
- Or use: `flyctl secrets set KEY=VALUE`

---

## ✅ Verify Deployment

After deploying, test these endpoints:

```bash
# Health check
curl https://your-app.railway.app/health

# Login endpoint
curl -X POST https://your-app.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo_user","password":"Demo1234"}'

# Access frontend
https://your-app.railway.app/static/login.html
```

---

## 🆓 FREE Tier Limits

### **Railway**
- 500 hours/month (free)
- 5 shared CPU cores
- 5GB RAM
- Good for: Small to medium apps

### **Render**
- Spins down after 15 min inactivity
- Cold starts: 30-60 seconds
- Good for: Hobby projects

### **Fly.io**
- 3 shared-cpu-1x 256MB VMs free
- Unlimited bandwidth
- Good for: Always-on apps

---

## 📊 Performance Tips

### **For Free Tier:**
1. ✅ Use database connection pooling
2. ✅ Cache frequently accessed data
3. ✅ Compress API responses
4. ✅ Use CDN for static files
5. ✅ Set auto-timeout for WebSocket

### **Reduce Costs:**
- Keep max users limit (10K)
- Use SQLite for <10K users (PostgreSQL for more)
- Enable caching headers
- Use lazy loading for images

---

## 🔐 Security Checklist

- ✅ Set strong environment variables
- ✅ Enable HTTPS (automatic on all platforms)
- ✅ Set CORS properly
- ✅ Rotate Stripe keys
- ✅ Monitor error logs
- ✅ Use rate limiting

---

## 📈 Scale When Ready

When you exceed free tier limits:

### **Railway → Paid**
- $5/GB memory/month
- $0.50/vCPU/month
- Good scaling up

### **Render → Paid**
- $7/month per service
- Predictable pricing
- No cold starts

### **AWS/GCP → Paid**
- Pay for what you use
- Most expensive
- Best for scale

---

## 🆘 Troubleshooting

### **App won't start**
```bash
# Check logs
railway logs
# or
render logs
```

### **Database connection error**
- Verify DATABASE_URL environment variable
- Ensure SQLite file permissions (railway auto-handles)

### **WebSocket connection fails**
- Verify WSS is enabled (automatic on HTTPS)
- Check firewall/port settings

### **Static files not loading**
- Verify path is `/static/`
- Check file exists in repository

---

## 📝 Example: Deploy to Railway in 3 Steps

### **Step 1: GitHub**
```bash
git push origin main
```

### **Step 2: Railway**
- Connect GitHub account
- Select your repo
- Click "Deploy"

### **Step 3: Access**
```
https://woeidchat-xxx.railway.app/static/login.html
```

✅ **DONE! Your app is live!**

---

## 🎯 What Users See

1. **Visit your app**: `https://woeidchat-xxx.railway.app/static/login.html`
2. **Register account**: Create free account
3. **Login**: Access dashboard
4. **Start messaging**: All features FREE! ✅

---

## 📞 Support

- Railway: [docs.railway.app](https://docs.railway.app)
- Render: [render.com/docs](https://render.com/docs)
- Fly.io: [fly.io/docs](https://fly.io/docs)

---

**🚀 Your app is ready to deploy! Choose your platform and go live in minutes!**

Version: 1.0 | Last Updated: 2026-04-18
