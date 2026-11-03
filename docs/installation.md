# Deploy the Laravel web app and separate AI kernel

The master branch is an index. The web-interface branch is now a Laravel 13/PHP 8.3+ application;
the kernel branch remains a separate Python service. Do not merge the branches.

Clone the web branch into an empty aaPanel site directory:

```sh
git clone --branch web-interface --single-branch https://github.com/parsabe/Clifford.git .
composer install --no-dev --prefer-dist --optimize-autoloader
cp .env.example .env  # only when absent
php artisan clifford:install
php artisan optimize
php artisan clifford:check
```

Set aaPanel Running Directory to **public/**, select PHP 8.3+, enable HTTPS for
**clifford.parsabe.com**, and add the Laravel rewrite and voice-only WebSocket proxy configuration.
[Complete aaPanel instructions](aapanel.md) explain PHP permissions, buffering and timeouts.
No Node build or web database is required. The owner login and kernel token are configured privately;
the browser never receives the long-lived kernel token.

Install/run the kernel in its own directory according to its README:

```sh
git clone --branch kernel --single-branch https://github.com/parsabe/Clifford.git clifford-kernel
```

Keep the kernel privately reachable, typically at 127.0.0.1:8000, with one worker. Update it to include
POST /v1/voice/tickets. Leave its WEB_ROOT empty: Laravel now serves the web pages. Install local
Ollama gemma3:12b and the Vosk speech model, and run its actual model readiness script. The separate
Debian package effort remains paused pending Ubuntu/architecture details. aaPanel handles public
ports 80/443 and certificates; do not run an additional conflicting Caddy listener.

A 12GB server may be tight for quantized Gemma 3 12B; small context settings are included. Real inference
speed, recognition and speaker echo still need testing on your hardware. The Laravel conversion has
passed feature and browser protocol-fixture checks, not a real deployment to your domain.
