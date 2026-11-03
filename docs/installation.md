# Install the private kernel and Laravel site

Clone kernel and web-interface separately; do not merge branches. The kernel now accepts only Unix
socket traffic, with no shared access token or HTTP backend URL. The Laravel site has no custom
password hash; aaPanel site Password Access protects it.

1. Install the kernel branch in a service-readable root-owned location such as /opt/clifford/kernel.
   Install Python dependencies, local Ollama/Gemma and Vosk according to its README.
2. From the kernel checkout run `sudo ./scripts/install-service.sh www`, replacing www with the
   site's actual PHP-FPM/Nginx account. Restart PHP-FPM and Nginx so group access takes effect.
3. Deploy the web-interface branch, including hidden files. Preserve .env and storage on updates.
4. Run composer install, php artisan optimize:clear, php artisan clifford:install --no-interaction,
   php artisan optimize and php artisan clifford:check.
5. Set aaPanel root to public/, enable SSL and server-wide Password Access, and apply the supplied
   FastCGI parameters and Unix-socket voice proxy. Follow [the complete guide](aapanel.md).

The installer removes old backend-token, backend-timeout, custom-password-hash and old HTTP URL
settings automatically. It asks no secret/password questions, preserves unrelated fields and an
existing APP_KEY, and generates Laravel's encryption key when absent. CLIFFORD_SOCKET_PATH defaults
to /run/clifford/api.sock on both sides. Internal timeouts remain bounded without a user setting.

The .deb build is still paused pending OS/architecture details. Its older Caddy/Docker recipes are
not the current aaPanel installation path. Live target-server Gemma/physical voice and DNS/certificate
activation still require verification. A 12GB server may be tight for quantized Gemma 3 12B.
