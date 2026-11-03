# aaPanel installation

Use the **web-interface** branch for this PHP application; the Python AI server remains on **kernel**.
No branches are merged. Laravel does not run Gemma or replace the kernel service.

1. Install PHP 8.3+ in aaPanel with ctype, curl, dom, fileinfo, filter, hash, mbstring, openssl, pcre,
   PDO, session, tokenizer and XML support. Install Composer. The application uses file sessions/cache;
   no MySQL database, Node build or queue worker is required for this version.
2. Create the site `clifford.parsabe.com` and clone this branch into its site directory:
   `git clone --branch web-interface --single-branch https://github.com/parsabe/Clifford.git .`
   The destination must be empty. Use PHP 8.3+ consistently for CLI Composer/artisan and PHP-FPM.
3. Run `composer install --no-dev --prefer-dist --optimize-autoloader`, copy `.env.example` to `.env`
   if absent, then run `php artisan clifford:install`. Enter the private kernel URL/token and choose a
   web login password. Do not share the token or .env. The command generates APP_KEY if absent.
4. Give the site's PHP-FPM user write access to **storage/** and **bootstrap/cache/**. Keep source and
   vendor code read-only to that user where practical; `.env` must only be readable by the deployment
   owner and PHP-FPM user. A mode-0600 .env must be owned by the site's actual PHP-FPM user. Do not use
   chmod 777. Run `php artisan optimize` after configuration.
5. Set aaPanel's **Running Directory** / document root to **public/**. Add the Laravel rewrite rule
   and voice WebSocket location from `aapanel-nginx.conf` to the correct parts of the site configuration.
   Disable FastCGI buffering for this site's existing PHP handler and allow a 300-second read timeout.
   In this site's PHP-FPM pool, allow request_terminate_timeout >= 300 seconds and max_execution_time >= 300.
6. Point DNS for `clifford.parsabe.com` at the server, allow ports 80/443, and issue/enable Let's Encrypt
   SSL through aaPanel. Enable redirect to HTTPS. Do not also run Caddy on ports 80/443 on this host.
7. Keep the updated kernel branch running privately at `127.0.0.1:8000`; Ollama stays private too.
   The kernel must include the `/v1/voice/tickets` addition. Leave kernel WEB_ROOT empty: Laravel now
   serves the UI. Check the kernel's live model readiness script independently.
8. Run `php artisan clifford:check` and resolve reported kernel/model problems. Open `https://clifford.parsabe.com/`, sign in with your web password, and enable voice once.
   The browser receives only a 30-second single-use voice ticket, never the main backend token.

If web and kernel are on different servers, use HTTPS to the private kernel, authorize that network
path, and adjust the server-side voice proxy upstream. Do not use public unencrypted HTTP.
No native phone/watch application is included; the web app works in supported mobile browsers.

## Updates

Run `git pull --ff-only`, `composer install --no-dev --prefer-dist --optimize-autoloader`, and
`php artisan optimize`. Preserve `.env`, sessions and app keys. Do not run key:generate on every
update, as that invalidates encrypted sessions. Restart/reload the site's PHP-FPM if OPcache requires it.

For streaming, PHP allow_url_fopen must be enabled. Composer CLI may also require proc_open; review aaPanel's disabled-functions settings for the correct CLI/PHP-FPM versions rather than globally weakening unrelated sites.
