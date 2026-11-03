<?php

namespace Tests\Feature;

use App\Services\KernelClient;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class CliffordTest extends TestCase
{
    private $socket;

    private string $socketPath;

    protected function setUp(): void
    {
        parent::setUp();
        $this->socketPath = sys_get_temp_dir().'/clifford-test-'.bin2hex(random_bytes(8)).'.sock';
        $this->socket = stream_socket_server('unix://'.$this->socketPath);
        config(['app.key' => 'base64:'.base64_encode(str_repeat('k', 32)), 'session.secure' => false,
            'clifford.socket_path' => $this->socketPath]);
        Http::preventStrayRequests();
    }

    protected function tearDown(): void
    {
        fclose($this->socket);
        @unlink($this->socketPath);
        parent::tearDown();
    }

    private function site()
    {
        return $this->withServerVariables(['CLIFFORD_SITE_PROTECTED' => '1', 'REMOTE_USER' => 'owner']);
    }

    public function test_unprotected_production_requests_fail_closed(): void
    {
        $this->get('/')->assertStatus(503);
        $this->getJson('/api/providers')->assertStatus(503);
        $this->postJson('/api/voice/ticket')->assertStatus(503);
        Http::assertNothingSent();
    }

    public function test_client_headers_cannot_spoof_site_protection(): void
    {
        $this->withHeaders(['CLIFFORD_SITE_PROTECTED' => '1', 'REMOTE_USER' => 'owner',
            'Authorization' => 'Basic '.base64_encode('owner:fake')])
            ->getJson('/api/providers')->assertStatus(503);
        Http::assertNothingSent();
    }

    public function test_site_requires_an_authenticated_nginx_user(): void
    {
        $this->withServerVariables(['CLIFFORD_SITE_PROTECTED' => '1'])
            ->get('/')->assertStatus(401);
    }

    public function test_console_has_no_custom_login_or_backend_credentials(): void
    {
        $this->site()->get('/')->assertOk()->assertSee('CLIFFORD')
            ->assertDontSee('Backend access token')->assertDontSee('Sign out');
        $this->get('/login')->assertNotFound();
    }

    public function test_provider_proxy_uses_no_authorization_header(): void
    {
        Http::fake(['localhost/v1/providers' => Http::response([
            'model' => 'gemma3:12b', 'assistant_name' => 'Clifford', 'wake_phrase' => 'Clifford',
            'private' => 'must-not-be-forwarded',
        ])]);
        $this->site()->getJson('/api/providers')->assertOk()->assertJsonPath('model', 'gemma3:12b')
            ->assertDontSee('must-not-be-forwarded');
        Http::assertSent(fn ($request) => ! $request->hasHeader('Authorization'));
    }

    public function test_sse_proxy_preserves_frames(): void
    {
        $frames = "event: assistant.delta\ndata: {\"type\":\"assistant.delta\",\"payload\":{\"text\":\"Hello\"}}\n\n";
        $this->mock(KernelClient::class, function ($mock) use ($frames) {
            $mock->shouldReceive('assertAvailable')->once()->andReturn($this->socketPath);
            $mock->shouldReceive('stream')->once()->with('/v1/chat/stream', ['text' => 'Hello'], \Mockery::type('callable'))
                ->andReturnUsing(function ($path, $body, $write) use ($frames) {
                    $write($frames);
                });
        });
        $response = $this->site()->postJson('/api/chat/stream', ['text' => 'Hello']);
        $response->assertOk()->assertHeader('Content-Type', 'text/event-stream; charset=UTF-8')
            ->assertHeader('X-Accel-Buffering', 'no');
        $this->assertSame($frames, $response->streamedContent());
    }

    public function test_invalid_input_never_reaches_kernel(): void
    {
        $this->site()->postJson('/api/chat/stream', ['text' => '', 'session_id' => '../../etc/passwd'])
            ->assertUnprocessable();
        Http::assertNothingSent();
    }

    public function test_kernel_error_is_redacted(): void
    {
        Http::fake(['localhost/*' => Http::response('private diagnostic', 500)]);
        $this->site()->getJson('/api/providers')->assertStatus(502)->assertDontSee('private diagnostic');
    }

    public function test_voice_ticket_is_scoped_and_automatic(): void
    {
        Http::fake(['localhost/v1/voice/tickets' => Http::response(['ticket' => 'one-use-ticket',
            'expires_in' => 30, 'private' => 'do-not-forward'])]);
        $this->site()->postJson('/api/voice/ticket')->assertOk()->assertJsonPath('ticket', 'one-use-ticket')
            ->assertJsonPath('websocket_path', '/clifford-voice')->assertDontSee('do-not-forward');
    }

    public function test_missing_socket_does_not_fall_back_to_tcp(): void
    {
        config(['clifford.socket_path' => '/missing/kernel.sock']);
        $this->site()->getJson('/api/providers')->assertStatus(503)
            ->assertJsonPath('error.code', 'kernel_socket_unavailable');
        Http::assertNothingSent();
    }

    public function test_installer_removes_retired_fields_without_password_prompts(): void
    {
        $directory = sys_get_temp_dir().'/clifford-env-'.bin2hex(random_bytes(8));
        mkdir($directory, 0700);
        $path = $directory.'/.env';
        file_put_contents($path, "APP_KEY=keep-existing-key\nUNRELATED_SETTING=preserve-me\nCLIFFORD_BACKEND_TOKEN=old-value\nCLIFFORD_BACKEND_TIMEOUT=240\nCLIFFORD_WEB_PASSWORD_HASH=old-value\nCLIFFORD_AUTH_SECRET=old-value\n");
        $this->app->useEnvironmentPath($directory);
        $this->app->loadEnvironmentFrom('.env');
        try {
            $this->artisan('clifford:install')->assertSuccessful();
            $contents = file_get_contents($path);
            $this->assertStringContainsString('UNRELATED_SETTING=preserve-me', $contents);
            $this->assertStringContainsString('APP_KEY=keep-existing-key', $contents);
            foreach (['CLIFFORD_BACKEND_TOKEN=', 'CLIFFORD_BACKEND_TIMEOUT=',
                'CLIFFORD_WEB_PASSWORD_HASH=', 'CLIFFORD_AUTH_SECRET='] as $retired) {
                $this->assertStringNotContainsString($retired, $contents);
            }
            $this->assertStringContainsString('CLIFFORD_SOCKET_PATH=/run/clifford/api.sock', $contents);
            $this->assertSame(0600, fileperms($path) & 0777);
        } finally {
            unlink($path);
            rmdir($directory);
        }
    }

    public function test_empty_app_key_is_generated_even_with_a_stale_cached_key(): void
    {
        $directory = sys_get_temp_dir().'/clifford-new-env-'.bin2hex(random_bytes(8));
        mkdir($directory, 0700);
        $path = $directory.'/.env';
        file_put_contents($path, "APP_KEY=\n");
        $this->app->useEnvironmentPath($directory);
        $this->app->loadEnvironmentFrom('.env');
        try {
            $this->artisan('clifford:install')->assertSuccessful();
            $contents = file_get_contents($path);
            $this->assertMatchesRegularExpression('/^APP_KEY=base64:[A-Za-z0-9+\/=]+$/m', $contents);
            $this->assertSame(0600, fileperms($path) & 0777);
        } finally {
            unlink($path);
            rmdir($directory);
        }
    }
}
