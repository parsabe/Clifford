# Clifford Laravel web application

Laravel 13/PHP 8.3+ web interface for aaPanel, with the site document root set to **public/**.
The separate `kernel` branch runs local Gemma/Vosk. No branches are merged.

**No shared backend token or custom Laravel web password is required.** Kernel requests use a
filesystem-protected Unix socket. aaPanel/Nginx Password Access protects the public website.
Request timeouts are bounded internally; there is no timeout field to fill in.

## Install or update

From the application directory:

```sh
composer install --no-dev --prefer-dist --optimize-autoloader
# Copy the template only on a first install; preserve existing .env on updates.
cp -n .env.example .env
php artisan optimize:clear
php artisan clifford:install --no-interaction
php artisan optimize
php artisan clifford:check
```

`clifford:install` asks no credential questions. It removes retired custom authentication fields
from an existing .env, preserves unrelated values and APP_KEY, and generates Laravel's standard
encryption key only when absent. Do not regenerate APP_KEY on every update.

The only Clifford-specific web setting is the local socket path, with a working service default:

```dotenv
CLIFFORD_SOCKET_PATH=/run/clifford/api.sock
```

Install/start the updated kernel Unix-socket service, grant the site's PHP-FPM/Nginx account access
to the `clifford-web` group, restart those services, and apply the aaPanel settings in
[deploy/README.md](deploy/README.md). Keep the kernel off TCP. Missing socket permissions are a real
setup error; Laravel does not fall back to an unprotected HTTP port.

In aaPanel, set Running Directory to public/, enable SSL for clifford.parsabe.com, enable site-wide
Password Access, and add the supplied FastCGI parameters/rewrite/voice proxy. Production requests
without the perimeter configuration fail closed. There is no application login page or custom web
password hash. Local development at a loopback address with APP_ENV=local can run without site auth.

PHP cURL is required for streaming over Unix sockets. There is no Node/Vite build or web database.
File sessions/cache and the standard Laravel app key support CSRF protection. The browser receives
only automatic short-lived voice tickets, never a persistent backend credential.

Clifford's name and wake phrase are Clifford. Enable voice once and grant microphone permission;
responses speak automatically using device voices, and talking can interrupt playback/generation.
Physical recognition/echo and live Gemma performance still require device testing. No email, native
phone/watch app or unattended scheduler is included.

Tests: `php artisan test`, `vendor/bin/pint --test`, `node tests/voice.test.mjs`.
See [validation](deploy/VALIDATION.md) for scope and limitations.

[Kernel](https://github.com/parsabe/Clifford/tree/kernel) ·
[Documentation](https://github.com/parsabe/Clifford/tree/documentation) ·
[Branch index](https://github.com/parsabe/Clifford/tree/master)
