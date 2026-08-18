import os
import subprocess

def run_cmd(cmd):
    print(f"Executing: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"STDOUT: {res.stdout}")
    print(f"STDERR: {res.stderr}")
    return res.returncode == 0

def main():
    domain = "3dceci.daosrl.com.ar"
    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    
    # 1. SSL Certificate generation if not present
    if not os.path.exists(cert_path):
        print(f"Certificate for {domain} not found. Acquiring via certbot standalone...")
        # Stop port 80 container to free the port for certbot
        run_cmd("docker stop dao-metricas-nginx")
        # Run certbot
        certbot_cmd = f"certbot certonly --standalone -d {domain} --non-interactive --agree-tos --email lvdandrea@users.noreply.github.com"
        success = run_cmd(certbot_cmd)
        # Restart port 80 container
        run_cmd("docker start dao-metricas-nginx")
        if not success:
            print("Failed to acquire SSL certificate.")
            return
    else:
        print(f"Certificate for {domain} already exists.")

    # 2. Update app-dao-ops central Nginx config
    nginx_conf_path = "/opt/docker/app-dao-ops/nginx/app-dao-ops.conf"
    if os.path.exists(nginx_conf_path):
        with open(nginx_conf_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if domain in content:
            print(f"Nginx config already contains mapping for {domain}.")
        else:
            print(f"Adding server block for {domain} to Nginx config...")
            server_block = f"""

server {{
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name {domain};

    ssl_certificate     /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    location / {{
        proxy_pass http://161.97.110.140:8085;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }}
}}
"""
            with open(nginx_conf_path, "a", encoding="utf-8") as f:
                f.write(server_block)
            
            # Reload Nginx central proxy
            print("Reloading app-dao-ops-nginx-1...")
            run_cmd("docker exec app-dao-ops-nginx-1 nginx -s reload")
    else:
        print(f"Nginx config path {nginx_conf_path} not found on this system.")

if __name__ == "__main__":
    main()
