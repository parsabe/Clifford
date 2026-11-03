# Verified scope

The Laravel conversion was validated with PHP 8.3.36 and Laravel 13.39.0:

- 11 Laravel feature tests passed (59 assertions): private login/logout, guest rejection, owner setup,
  no browser exposure of the kernel token, streamed upstream frames, input validation, error redaction,
  voice-scoped ticket proxying, remote HTTP rejection and invalid metadata handling.
- Five JavaScript voice-state tests passed. Module syntax checks passed.
- PHP platform requirements, Composer schema/lock validation, Pint style and artisan optimize passed.
- A real Laravel HTTP server authenticated a browser session, rejected a missing CSRF token with 419,
  proxied a scoped voice ticket and streamed a local test kernel response. The first frame arrived
  in about 14ms while the fixture intentionally delayed completion for two seconds.
- Chromium passed login, automatic device speech, voice-ticket first-frame format, interruption,
  replacement command, mic release, mobile layout and logout with explicit synthetic device/transcript
  fixtures. No JavaScript errors occurred; the main kernel token was absent from the browser page.
- Nginx validated the supplied rewrite/WebSocket/hidden-file rules in a representative PHP site config.
- The kernel branch passed 46 Python tests including ticket expiry, replay prevention and voice-only scope.

The HTTP/device fixtures are development tests, not a runtime fake model provider. Actual Gemma
inference, physical microphone acoustics, remote aaPanel PHP-FPM deployment, public DNS and Let's
Encrypt issuance have not been verified by this cloud session. A diagnostic outside the test-kernel
container correctly reported backend_unavailable; inside the explicitly local protocol fixture it
passed. This does not establish live model readiness. Use the real kernel readiness script and
php artisan clifford:check on the target server, then verify text/voice behavior in the HTTPS browser.

Dependencies were fetched through verified canonical Git sources because this cloud proxy denies
GitHub's archive API. Development source installs emitted duplicate-class-map warnings from vendor
repositories that include extra test/source trees. The canonical application classes were selected,
all feature tests passed, and the dependency audit reported no advisories. Normal aaPanel installs
use Composer's locked dist artifacts. No vendor directories, app keys, passwords, .env files, runtime
caches or logs are committed.
