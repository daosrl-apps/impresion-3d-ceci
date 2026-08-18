import os
import subprocess
import json
import re

def run_cmd(cmd):
    print(f"Executing: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"STDOUT: {res.stdout}")
    print(f"STDERR: {res.stderr}")
    return res.returncode == 0

def get_gateway_ip():
    try:
        cmd = "docker inspect app-dao-ops-nginx-1"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        data = json.loads(res.stdout)
        if data and len(data) > 0:
            networks = data[0].get("NetworkSettings", {}).get("Networks", {})
            for net_name, net_info in networks.items():
                gw = net_info.get("Gateway")
                if gw:
                    return gw
    except Exception as e:
        print(f"Error detecting gateway IP: {e}")
    return "172.17.0.1"

def main():
    domain = "3dceci.daosrl.com.ar"
    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    
    # 1. SSL Certificate generation if not present
    if not os.path.exists(cert_path):
        print(f"Certificate for {domain} not found. Acquiring via certbot standalone...")
        run_cmd("docker stop dao-metricas-nginx")
        certbot_cmd = f"certbot certonly --standalone -d {domain} --non-interactive --agree-tos --email lvdandrea@users.noreply.github.com"
        success = run_cmd(certbot_cmd)
        run_cmd("docker start dao-metricas-nginx")
        if not success:
            print("Failed to acquire SSL certificate.")
            return
    else:
        print(f"Certificate for {domain} already exists.")

    # 2. Detect gateway IP
    gw_ip = get_gateway_ip()
    print(f"Using host gateway IP: {gw_ip}")

    # 3. Update app-dao-ops central Nginx config
    nginx_conf_path = "/opt/docker/app-dao-ops/nginx/app-dao-ops.conf"
    if os.path.exists(nginx_conf_path):
        with open(nginx_conf_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Clean up any existing 3dceci server block to prevent duplicates or stale IPs
        # We find the position of the server block for 3dceci.daosrl.com.ar
        if "server_name 3dceci.daosrl.com.ar;" in content:
            print("Removing existing 3dceci server block to update it...")
            # We split the file by the server block start
            parts = content.split("server_name 3dceci.daosrl.com.ar;")
            # The part before "server_name" contains the start of the server block: "server {"
            # We search backwards for the last "server {" in parts[0]
            start_idx = parts[0].rfind("server {")
            if start_idx != -1:
                # We want to remove from start_idx to the matching closing brace in parts[1]
                # To find the matching closing brace, we count braces in parts[1]
                brace_count = 1 # The "server {" has 1 open brace
                end_idx = -1
                for i, char in enumerate(parts[1]):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                if end_idx != -1:
                    # Remove the block
                    content = parts[0][:start_idx] + parts[1][end_idx+1:]
                    print("Stale server block removed successfully.")

        # Append the new server block with correct gateway IP
        print(f"Adding server block for {domain} targeting {gw_ip}:8085...")
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
        proxy_pass http://{gw_ip}:8085;
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
        # Save updated config
        with open(nginx_conf_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + server_block)
        
        # Reload Nginx central proxy
        print("Reloading app-dao-ops-nginx-1...")
        run_cmd("docker exec app-dao-ops-nginx-1 nginx -s reload")
    else:
        print(f"Nginx config path {nginx_conf_path} not found on this system.")

if __name__ == "__main__":
    main()
