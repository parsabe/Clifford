# aaPanel installation: private socket, no custom token/password fields

The `web-interface` branch is Laravel; `kernel` is the separate AI service. Keep them separate.
Use PHP 8.3+ for both CLI and PHP-FPM, with cURL, ctype, dom, fileinfo, hash, mbstring, openssl, PDO,
session, tokenizer and XML. No paid-provider keys, web database, Node build or queue worker are required.

## 1. Kernel service

Install kernel dependencies and local Gemma/Vosk using its README, preferably in a root-owned
`/opt/clifford/kernel` directory. Then, from that kernel checkout:

```sh
sudo ./scripts/install-service.sh www
sudo systemctl status clifford --no-pager
```

`www` is the usual aaPanel PHP-FPM/Nginx account; substitute the actual account on your server.
The helper uses the existing .venv and data, removes the retired shared-token setting, installs a
source systemd service and adds that account to `clifford-web`. It does not build the paused .deb.
It preserves existing data and only changes ownership within the kernel's project data/ directory.
Custom data paths require corresponding service permissions/ReadWritePaths adjustments.

The kernel listens only at **/run/clifford/api.sock**. Its directory is private (0750), and the group
is clifford-web. The service disables proxy-header rewriting; TCP requests are rejected by the API.
Use the provided start/service commands. Never put a no-token kernel on an unrestricted TCP port.

If the helper reports that the service cannot execute Python, the virtual environment or its base
Python is inside a private home directory. Recreate it using system Python 3.12 or a service-readable
managed Python under /opt, keeping installed code outside /root and /home. The helper checks access
before starting. For example, set UV_PYTHON_INSTALL_DIR=/opt/clifford/python when provisioning uv's
managed interpreter and recreating the kernel venv. Back up any custom environment before recreating it.

Restart the site's PHP-FPM and Nginx in aaPanel after changing group membership.

## 2. Laravel

Download the web-interface branch including hidden files, or clone it into an empty site directory.
Keep .env, storage and existing app keys on updates. If files were moved without Git metadata, update
from the branch ZIP; Git is not required to run the app. No vendor/runtime files are shipped in Git.

```sh
composer install --no-dev --prefer-dist --optimize-autoloader
# On first install only, if .env does not exist:
cp -n .env.example .env
php artisan optimize:clear
php artisan clifford:install --no-interaction
php artisan optimize
php artisan clifford:check
```

The installer asks no token/password questions. It deletes retired backend-token, backend-timeout,
custom-password-hash and old backend-URL fields, while preserving unrelated settings and APP_KEY.
Laravel's standard encryption key is generated automatically if absent. Only CLIFFORD_SOCKET_PATH
remains as a Clifford web setting; its default matches the service. Do not paste secrets into chat.

Give PHP-FPM write access to storage/ and bootstrap/cache/. Keep code read-only where practical.
The private .env must be readable by the actual PHP-FPM account; mode 0600 requires the matching
owner. Never expose the project root or use chmod 777.

## 3. aaPanel site access, PHP parameters and HTTPS

1. Set Running Directory/document root to **public/** and enable PHP 8.3+.
2. Enable aaPanel's site Password Access. Ensure Nginx's generated auth_basic/auth_basic_user_file
   directives apply at **server scope**, including the voice location and all API routes. Manage
   this site password in aaPanel; there is no custom password field in the Laravel .env.
3. In the site's existing PHP/FastCGI location (alongside the normal fastcgi_params/include), add:

   ```nginx
   fastcgi_param CLIFFORD_SITE_PROTECTED 1;
   fastcgi_param REMOTE_USER $remote_user;
   fastcgi_buffering off;
   fastcgi_read_timeout 300s;
   fastcgi_send_timeout 300s;
   ```

   Set the protection marker only after server-wide Password Access is active. These are server
   FastCGI parameters, not proxy/request headers. Laravel rejects client attempts to spoof them.
4. Add the rewrite and Unix-socket voice location from aapanel-nginx.conf. There is no backend HTTP
   upstream URL or shared token. PHP cURL sends JSON/SSE over the private Unix socket.
5. Set this PHP-FPM pool's request_terminate_timeout and max_execution_time to at least 300 seconds.
6. Point clifford.parsabe.com DNS at your server and enable Let's Encrypt SSL/HTTPS redirect in aaPanel.
   aaPanel owns ports 80/443. Do not run a conflicting Caddy listener on them.
7. Reload the site and open https://clifford.parsabe.com/. The browser uses aaPanel's normal HTTP
   authentication prompt, then opens the console directly. There is no separate Laravel login page.

If the app returns 503, check the socket service/permissions and the two FastCGI parameters. A 401
from the app means the authenticated REMOTE_USER parameter is absent. Check site Password Access.
POST requests still require Laravel CSRF/session protection. Voice uses an automatically generated,
30-second single-use ticket; it is never a value you must fill in .env.

## Verification

```sh
sudo systemctl status clifford --no-pager
sudo journalctl -u clifford -n 50 --no-pager
php artisan clifford:check
```

Kernel TCP access must fail. Socket, model and speech checks must pass on the real host before voice
is considered ready. Test actual microphone/echo behavior in the HTTPS browser. Native apps remain
future work; this deployment supports the responsive browser UI through the protected site.
