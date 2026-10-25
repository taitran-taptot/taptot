# Deploy TAPTOT lên VPS (Ubuntu 24.04)

Stack: PostgreSQL + uvicorn (127.0.0.1:8000) + `next start` (127.0.0.1:3000) + nginx (80/443). Không dùng Docker/Railway.

## 1. Gói hệ thống

```bash
sudo apt update
sudo apt install -y postgresql nginx python3 python3-venv python3-pip git certbot python3-certbot-nginx
# Node 20+
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

## 2. User, thư mục, Postgres

```bash
sudo useradd --system --create-home --home-dir /opt/taptot --shell /usr/sbin/nologin taptot
sudo mkdir -p /opt/taptot /var/lib/taptot/uploads /etc/taptot /var/www/certbot
sudo chown -R taptot:taptot /opt/taptot /var/lib/taptot

sudo -u postgres psql -c "CREATE USER taptot WITH PASSWORD 'CHANGE_ME';"
sudo -u postgres psql -c "CREATE DATABASE taptot OWNER taptot;"
```

Clone repo vào `/opt/taptot` (hoặc rsync từ máy dev). Schema + seed chạy lúc API start (`ensure_*`).

## 3. API

```bash
sudo -u taptot python3 -m venv /opt/taptot/venv
sudo -u taptot /opt/taptot/venv/bin/pip install -r /opt/taptot/api/requirements.txt
sudo cp /opt/taptot/api/.env.example /etc/taptot/api.env
sudo chmod 640 /etc/taptot/api.env
sudo chown root:taptot /etc/taptot/api.env
```

Sửa `/etc/taptot/api.env` tối thiểu:

```
APP_ENV=production
DEBUG=false
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
DATABASE_URL=postgresql+psycopg://taptot:CHANGE_ME@127.0.0.1:5432/taptot
CORS_ORIGINS=https://taptot.vn,https://www.taptot.vn
FRONTEND_URL=https://taptot.vn
MEDIA_BASE_URL=https://taptot.vn/media
UPLOAD_DIR=/var/lib/taptot/uploads
```

```bash
sudo cp /opt/taptot/deploy/systemd/taptot-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now taptot-api
curl -sS http://127.0.0.1:8000/health
```

Lần đầu start, migration/seed chạy nền vài chục giây — nếu `/health` OK mà catalog 404, đợi rồi restart không cần.

## 4. Frontend

```bash
cd /opt/taptot/frontend
sudo -u taptot bash -lc 'cd /opt/taptot/frontend && npm ci'
sudo tee /etc/taptot/web.env >/dev/null <<'EOF'
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_MEDIA_BASE=/media
NEXT_PUBLIC_REQUIRE_REDEEM_CODE=true
NEXT_PUBLIC_TURNSTILE_SITE_KEY=
EOF
sudo chown root:taptot /etc/taptot/web.env
sudo chmod 640 /etc/taptot/web.env
# NEXT_PUBLIC_* được bake lúc build:
sudo -u taptot bash -lc 'set -a; . /etc/taptot/web.env; set +a; cd /opt/taptot/frontend && npm run build'
sudo cp /opt/taptot/deploy/systemd/taptot-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now taptot-web
```

## 5. Nginx + TLS

Sửa `server_name` trong `deploy/nginx/taptot.conf`, rồi:

```bash
sudo cp /opt/taptot/deploy/nginx/taptot.conf /etc/nginx/sites-available/taptot
sudo ln -sf /etc/nginx/sites-available/taptot /etc/nginx/sites-enabled/taptot
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d taptot.vn -d www.taptot.vn
```

Timeout `/api/` là 180s (sinh lịch Challenge).

## 6. Deploy bản mới

```bash
cd /opt/taptot && sudo -u taptot git pull
sudo -u taptot /opt/taptot/venv/bin/pip install -r /opt/taptot/api/requirements.txt
sudo -u taptot bash -lc 'set -a; . /etc/taptot/web.env; set +a; cd /opt/taptot/frontend && npm ci && npm run build'
sudo systemctl restart taptot-api taptot-web
```

## Rollback schema

`040` xóa `trainer_assigned_plans` và cột `user_profiles` chết. `041` **DROP** `trainer_profiles` / `trainer_credentials` / `trainer_clients` (kể cả dữ liệu). Không restore tự động — backup Postgres trước lần deploy:

```bash
sudo -u postgres pg_dump taptot > /root/taptot-$(date +%F).sql
```
