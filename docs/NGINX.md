# Nginx Reverse Proxy

## Overview

Nginx acts as a single entry point for all Smart Irrigation services, providing reverse proxy functionality, routing requests to appropriate backend services, and optionally handling SSL/TLS termination.

**Port:** 80

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                           │
│                                                                                 │
│  Browser → http://localhost/                                                  │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         NGINX (:80)                                            │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Route Map                                          │   │
│  │                                                                          │   │
│  │  /             → web-dashboard:3000                                     │   │
│  │  /api/         → api-gateway:8080                                       │   │
│  │  /grafana/     → grafana:3000                                           │   │
│  │  /prometheus/  → prometheus:9090                                        │   │
│  │  /alertmanager/→ alertmanager:9093                                       │   │
│  │  /mlflow/      → mlflow:5000                                             │   │
│  │  /minio/       → minio:9001                                             │   │
│  │  /airflow/     → airflow:8085                                            │   │
│  │  /health       → (nginx returns 200)                                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
     ┌─────────────┬─────────────┼─────────────┬─────────────┐
     ▼             ▼             ▼             ▼             ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│Dashboard│   │   API   │   │ Grafana │   │Prometheus│  │  MLflow │
│  :3000  │   │ :8080   │   │  :3000  │   │  :9090  │  │  :5000  │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

---

## Configuration

### nginx.conf

```nginx
server {
    listen 80;
    server_name localhost;

    # Web Dashboard
    location / {
        proxy_pass http://web-dashboard:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API Gateway
    location /api/ {
        proxy_pass http://api-gateway:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Grafana
    location /grafana/ {
        proxy_pass http://grafana:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        rewrite ^/grafana/(.*) /$1 break;
    }

    # Prometheus
    location /prometheus/ {
        proxy_pass http://prometheus:9090/;
        rewrite ^/prometheus/(.*) /$1 break;
    }

    # Alertmanager
    location /alertmanager/ {
        proxy_pass http://alertmanager:9093/;
        rewrite ^/alertmanager/(.*) /$1 break;
    }

    # MLflow
    location /mlflow/ {
        proxy_pass http://mlflow:5000/;
        rewrite ^/mlflow/(.*) /$1 break;
    }

    # MinIO Console
    location /minio/ {
        proxy_pass http://minio:9001/;
        rewrite ^/minio/(.*) /$1 break;
    }

    # Airflow
    location /airflow/ {
        proxy_pass http://airflow:8085/;
        rewrite ^/airflow/(.*) /$1 break;
    }

    # Health check
    location /health {
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

## Docker Compose

### docker-compose.nginx.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./configs/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - irrigation_net
    depends_on:
      - web-dashboard
      - api-gateway
      - grafana
      - prometheus
      - alertmanager
      - mlflow
      - minio
      - airflow
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

---

## Starting with Nginx

```bash
# Full stack with Nginx
docker compose -f docker-compose.yml \
               -f docker-compose.app.yml \
               -f docker-compose.data.yml \
               -f docker-compose.ml.yml \
               -f docker-compose.monitoring.yml \
               -f docker-compose.nginx.yml up -d
```

---

## Access Routes

| URL | Service |
|-----|---------|
| http://localhost/ | Web Dashboard |
| http://localhost/api/v1/* | API Gateway |
| http://localhost/api/auth/* | Auth endpoints |
| http://localhost/grafana/ | Grafana |
| http://localhost/prometheus/ | Prometheus |
| http://localhost/alertmanager/ | Alertmanager |
| http://localhost/mlflow/ | MLflow |
| http://localhost/minio/ | MinIO Console |
| http://localhost/airflow/ | Airflow |
| http://localhost/health | Nginx health check |

---

## SSL/HTTPS Configuration

### Generate SSL Certificate

```bash
# Using Let's Encrypt (requires domain pointing to server)
sudo apt install certbot
sudo certbot --nginx -d your-domain.com

# Self-signed (for local testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem
```

### HTTPS Configuration

```nginx
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # ... proxy configuration same as HTTP
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name localhost;
    return 301 https://$server_name$request_uri;
}
```

---

## Load Balancing (Future)

For horizontal scaling:

```nginx
upstream dashboard_cluster {
    server web-dashboard-1:3000;
    server web-dashboard-2:3000;
    server web-dashboard-3:3000;
}

server {
    location / {
        proxy_pass http://dashboard_cluster;
    }
}
```

---

## Summary

| Aspect | Value |
|--------|-------|
| Port | 80 |
| Image | nginx:alpine |
| Config | docker/configs/nginx/nginx.conf |
| Compose | docker/docker-compose.nginx.yml |
| Routes | 8 backend services |

Nginx provides centralized access to all services through a single port, making deployment simpler and enabling future SSL termination.