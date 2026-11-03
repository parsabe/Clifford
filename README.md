# Clifford Laravel web application

This is the **web-interface** branch: a Laravel 13 application for PHP 8.3+, intended for aaPanel.
Set the site's document root to **public/**. The cyan waveform console uses Blade pages and static
JavaScript modules; there is no Node/Vite build requirement. Authentication, sessions, CSRF protection,
request validation, throttling, and the chat proxy are handled by Laravel.

The **kernel** branch remains a separate Python service for local Gemma 3 12B, Vosk speech recognition,
memory and tools. Laravel does not run the AI model itself. No component branches are merged.
No paid model API keys are used. The private kernel token stays in the PHP server configuration;
the browser signs in with an owner password and receives only single-use, voice-scoped tickets.

## Install on aaPanel

```sh
git clone --branch web-interface --single-branch https://github.com/parsabe/Clifford.git .
composer install --no-dev --prefer-dist --optimize-autoloader
cp .env.example .env                 # only if .env does not already exist
php artisan clifford:install
php artisan optimize
php artisan clifford:check
```

Use an empty site directory for the clone and PHP 8.3+ for both CLI and PHP-FPM. The interactive
installer asks privately for the kernel token and a web login password. Preserve APP_KEY and .env
on updates. Make storage/ and bootstrap/cache/ writable to the site's PHP-FPM user; .env is private.
No database setup is required: file-backed sessions/cache are the defaults.

In aaPanel:

1. Set Running Directory to **public/** and PHP to **8.3 or newer**.
2. Add the Laravel rewrite rule and voice-only WebSocket proxy from `deploy/aapanel-nginx.conf`.
3. Disable FastCGI response buffering for the site and allow long chat requests (300-second timeout).
4. Enable Let's Encrypt SSL for **clifford.parsabe.com**. aaPanel handles HTTPS; do not run a second
   Caddy listener on the same public ports.
5. Keep the updated **kernel** service privately running on `127.0.0.1:8000`; leave kernel WEB_ROOT
   empty because Laravel owns the browser UI now. Install Gemma/Vosk through the kernel guide.

Open the site root, sign in, then Enable voice once. Browser microphone permission is required.
Wake phrase and assistant name are Clifford. Speech output is automatic using local device voices;
interruption cancels playback/generation. Real microphone/echo and live Gemma performance still
need checking on your intended server and devices.

**Setting public/ alone is not sufficient:** Composer dependencies, private environment setup,
PHP permissions, the kernel service, SSL and the voice proxy must also be configured.
See [the complete aaPanel guide](deploy/README.md).

## Development and tests

```sh
composer install
php artisan test
vendor/bin/pint --test
node tests/voice.test.mjs
```

For local HTTP testing only, use SESSION_SECURE_COOKIE=false; keep it true on the HTTPS production
site. The application has one owner password, no public registration, email or native phone/watch app.
Text streams use the protected PHP proxy; voice PCM uses the ticket-authenticated Nginx WebSocket
route. The kernel must include POST /v1/voice/tickets; update kernel separately without merging.

[Kernel branch](https://github.com/parsabe/Clifford/tree/kernel) ·
[Documentation](https://github.com/parsabe/Clifford/tree/documentation) ·
[Branch index](https://github.com/parsabe/Clifford/tree/master)
