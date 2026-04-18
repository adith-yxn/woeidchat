# 🚀 Deployment Guide

Complete guide to deploy WoeidChat to various cloud platforms.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Heroku Deployment](#heroku-deployment)
4. [DigitalOcean Deployment](#digitalocean-deployment)
5. [AWS Deployment](#aws-deployment)
6. [Railway Deployment](#railway-deployment)
7. [Production Checklist](#production-checklist)

---

## Local Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/woeidchat.git
cd woeidchat

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python woeidchat_server_enhanced.py

# Run client in another terminal
python woeidchat_client_enhanced.py
```

### Development with Hot Reload

```bash
pip install uvicorn[standard]
uvicorn woeidchat_server_enhanced:app --reload --host 0.0.0.0 --port 8765
```

---

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f server

# Stop services
docker-compose down

# Clean up volumes
docker-compose down -v
```

### Manual Docker Commands

```bash
# Build image
docker build -t woeidchat-server:latest .

# Run container
docker run -d \
  --name woeidchat \
  -p 8765:8765 \
  -v woeidchat_data:/app/data \
  -v woeidchat_keys:/app/woeidchat_keys \
  -v woeidchat_uploads:/app/uploads \
  -e PYTHONUNBUFFERED=1 \
  woeidchat-server:latest

# Access logs
docker logs -f woeidchat

# Stop container
docker stop woeidchat

# Remove container
docker rm woeidchat
```

### Docker Hub Publishing

```bash
# Login to Docker Hub
docker login

# Tag image
docker tag woeidchat-server:latest yourusername/woeidchat:latest

# Push to registry
docker push yourusername/woeidchat:latest

# Pull and run from Docker Hub
docker run -d -p 8765:8765 yourusername/woeidchat:latest
```

---

## Heroku Deployment

### Prerequisites

- Heroku CLI installed: `curl https://cli-assets.heroku.com/install.sh | sh`
- Git repository initialized
- GitHub account

### Steps

```bash
# Step 1: Create Procfile
echo "web: uvicorn woeidchat_server_enhanced:app --host 0.0.0.0 --port \$PORT" > Procfile

# Step 2: Create runtime.txt
echo "python-3.10.13" > runtime.txt

# Step 3: Login to Heroku
heroku login

# Step 4: Create app
heroku create woeidchat-prod

# Step 5: Deploy
git push heroku main

# Step 6: View logs
heroku logs --tail

# Step 7: Open app
heroku open

# View app URL
heroku apps:info
```

### Configure Environment Variables

```bash
heroku config:set ENVIRONMENT=production
heroku config:set DEBUG=False
heroku config:set DATABASE_URL=postgresql://...

# View all vars
heroku config
```

### Scale Dynos

```bash
# Use more power
heroku ps:scale web=2

# Monitor
heroku ps
```

### Custom Domain

```bash
heroku domains:add woeidchat.com
# Add DNS CNAME record pointing to Heroku
```

---

## DigitalOcean Deployment

### Method 1: DigitalOcean App Platform

1. **Connect GitHub**
   - Go to Apps → Create App
   - Connect your GitHub repository

2. **Configure**
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `uvicorn woeidchat_server_enhanced:app --host 0.0.0.0 --port 8080`

3. **Environment Variables**
   ```
   ENVIRONMENT=production
   DEBUG=False
   PORT=8080
   ```

4. **Deploy** - Click Deploy

### Method 2: DigitalOcean Droplet + Docker

```bash
# 1. Create Droplet (Ubuntu 22.04 LTS)

# 2. SSH into droplet
ssh root@your-droplet-ip

# 3. Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git

# 4. Clone repository
git clone https://github.com/yourusername/woeidchat.git
cd woeidchat

# 5. Start services
docker-compose up -d

# 6. Setup Nginx reverse proxy
sudo apt-get install -y nginx certbot python3-certbot-nginx

# 7. Configure SSL
sudo certbot certonly --standalone -d yourdomain.com

# 8. Configure Nginx
sudo nano /etc/nginx/sites-available/default
# Add proxy to localhost:8765

sudo systemctl restart nginx
```

### Method 3: App Platform with Custom Domain

```bash
# In DigitalOcean Console:
1. Apps → woeidchat-app
2. Settings → App Spec
3. Edit domains
4. Add custom domain
5. Update DNS CNAME records
```

---

## AWS Deployment

### Option 1: AWS EC2 + Docker

```bash
# 1. Launch EC2 Instance
# - AMI: Ubuntu 22.04 LTS
# - Instance Type: t3.medium (or higher for production)
# - Security Group: Allow 80, 443, 8765

# 2. SSH into instance
ssh -i key.pem ubuntu@your-ec2-ip

# 3. Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git nginx

# 4. Clone and deploy
git clone https://github.com/yourusername/woeidchat.git
cd woeidchat
docker-compose up -d

# 5. Configure SSL
sudo certbot certonly --standalone -d woeidchat.yourdomain.com
sudo nginx -s reload
```

### Option 2: AWS Elastic Container Service (ECS)

```bash
# 1. Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker tag woeidchat-server:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/woeidchat:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/woeidchat:latest

# 2. Create ECS Cluster (via AWS Console)
# - Cluster name: woeidchat
# - VPC: default or custom
# - Task definition: Fargate

# 3. Create service
# - Launch type: Fargate
# - Task definition: woeidchat:latest
# - Desired count: 2-3
# - Load balancer: Application Load Balancer
```

### Option 3: AWS Lambda + API Gateway

```bash
# For microservices approach (advanced)
# Use Zappa to wrap FastAPI for Lambda
pip install zappa
zappa init
zappa deploy production
```

---

## Railway Deployment

### Easiest Cloud Deployment

```bash
# 1. Go to railway.app
# 2. Sign up with GitHub
# 3. Create new project
# 4. Select "Deploy from GitHub repo"
# 5. Choose woeidchat repository
# 6. Railway auto-detects FastAPI
# 7. Add environment variables
# 8. Deploy automatically on push

# Local testing:
pip install railway
railway run python woeidchat_server_enhanced.py
```

---

## SSL/TLS Setup

### Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d woeidchat.com

# Auto-renewal
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew
```

### Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name woeidchat.com;

    ssl_certificate /etc/letsencrypt/live/woeidchat.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/woeidchat.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8765/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name woeidchat.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Database Scaling

### SQLite → PostgreSQL Migration

```bash
# 1. Install PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib

# 2. Create database
sudo -u postgres createdb woeidchat
sudo -u postgres createuser woeidchat_user

# 3. Update server code
# Change: sqlite3.connect("woeidchat.db")
# To: psycopg2.connect("postgresql://user:pass@localhost/woeidchat")

# 4. Migrate data (if needed)
# Use migration script

# 5. Update requirements.txt
echo "psycopg2-binary>=2.9" >> requirements.txt
```

---

## Production Checklist

- [ ] Set `DEBUG = False` in production
- [ ] Enable HTTPS/SSL with valid certificate
- [ ] Use strong database passwords
- [ ] Set up database backups
- [ ] Configure rate limiting
- [ ] Enable CORS only for trusted origins
- [ ] Set up monitoring and alerts
- [ ] Configure auto-restart on failure
- [ ] Use process manager (systemd, supervisor)
- [ ] Enable access logs
- [ ] Set up CDN for file uploads
- [ ] Configure firewall rules
- [ ] Enable database encryption
- [ ] Set up regular security scans
- [ ] Document deployment process

---

## Monitoring & Logging

### Application Monitoring

```bash
# PM2 (process manager)
npm install -g pm2
pm2 start "uvicorn woeidchat_server_enhanced:app" --name woeidchat
pm2 logs woeidchat
pm2 monit
```

### Log Aggregation

```bash
# ELK Stack (Elasticsearch, Logstash, Kibana)
docker-compose -f elk-stack.yml up -d

# Or use cloud services:
# - LogRocket
# - Sentry
# - Datadog
```

### Performance Monitoring

```bash
# APM Tools
pip install elastic-apm

# Add to FastAPI:
from elasticapm.contrib.fastapi import ElasticAPM
app.add_middleware(ElasticAPM, client=apm_client)
```

---

## Scaling for Production

### Load Balancing

```bash
# Option 1: Nginx Load Balancer
upstream woeidchat_backend {
    server server1:8765;
    server server2:8765;
    server server3:8765;
}

server {
    listen 80;
    location / {
        proxy_pass http://woeidchat_backend;
    }
}

# Option 2: Cloud Load Balancer
# - AWS: Application Load Balancer (ALB)
# - DigitalOcean: Load Balancer
# - GCP: Cloud Load Balancing
```

### Database Replication

```bash
# PostgreSQL Replication
# Primary server streams WAL to replicas
# Improves read performance
```

### Caching Layer

```bash
# Redis Caching
pip install redis
# Cache user lists, public keys, etc.
```

---

## Backup & Disaster Recovery

```bash
# Automated backups
0 2 * * * /usr/local/bin/backup-woeidchat.sh

# Backup script
#!/bin/bash
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U woeidchat_user woeidchat > \
  $BACKUP_DIR/woeidchat_$TIMESTAMP.sql.gz
aws s3 cp $BACKUP_DIR/woeidchat_$TIMESTAMP.sql.gz s3://woeidchat-backups/

# Keep 30 days of backups
find $BACKUP_DIR -mtime +30 -delete
```

---

## Cost Optimization

| Platform | Estimated Monthly Cost |
|---|---|
| Heroku | $50-200 (Eco + Standard) |
| DigitalOcean | $5-40 (Droplet + App Platform) |
| Railway | Free tier + Pay-as-you-go |
| AWS | $10-100+ (varies by usage) |
| Self-hosted VPS | $5-50 |

---

## Support & Troubleshooting

For issues:
1. Check logs: `docker-compose logs server`
2. Test connectivity: `curl http://localhost:8765/docs`
3. Verify environment variables
4. Check database connection
5. Review firewall rules

See README.md for additional help.
