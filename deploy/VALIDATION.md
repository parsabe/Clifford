# Validation for removal of custom authentication settings

- The kernel passes 47 Python tests, including a real Uvicorn Unix socket and a separate TCP listener:
  no-token socket requests succeed; TCP requests fail with 403 even with forged forwarding headers.
- Laravel passes 12 feature tests covering aaPanel/FastCGI perimeter enforcement, header spoofing,
  missing authenticated site user, no custom login, no Authorization header to the kernel, SSE frames,
  input validation, error redaction, automatic scoped tickets, no TCP fallback and migration of old .env
  fields without prompts. Unrelated configuration and the existing Laravel app key are preserved.
- PHP 8.3 cURL is an explicit requirement. Streaming uses native cURL Unix sockets, not PHP's TCP stream
  wrapper, and remains internally bounded without a user-supplied timeout setting.
- Five JavaScript voice-state tests and PHP style/syntax checks are part of validation.

The site uses aaPanel/Nginx authentication instead of a custom Laravel password hash. Production
requests fail closed if the trusted FastCGI protection/user parameters are missing; the site must
actually enable server-wide Password Access before those parameters are set. Client request headers
cannot provide them. The kernel itself must be started on its filesystem-protected Unix socket with
proxy header rewriting disabled. This is a change of access boundary, not unauthenticated TCP exposure.

Model/microphone behavior remains unverified on the target server. Local integration tests use an
explicit deterministic provider and temporary model/database state; no fake provider is installed in
the application. The source service helper is provided but has not been run on the user's aaPanel host.
The .deb build remains paused. Live DNS/certificates and OS/PHP-FPM user permissions need target checks.

A real Nginx HTTP-authenticated test site, Laravel and the actual updated kernel were exercised
end to end over a shared private Unix socket. REST requests, CSRF rejection, ticket minting and the
Nginx voice WebSocket path passed without a backend token. Native cURL SSE delivered its first frame
in about 40ms before a deliberately delayed test reply completed. The voice socket correctly reported
a missing real Vosk model after accepting its ticket. The test PHP router models trusted FastCGI
server parameters from a private authenticated Nginx peer; a remote aaPanel PHP-FPM installation was
not provisioned by this session.

The browser also passed automatic speech, synthetic interruption/replacement, mic release and mobile layout over the socket architecture behind real Nginx site authentication. First-time app-key generation is covered even when an old key remains in cached configuration.
