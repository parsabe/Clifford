<?php

namespace Tests\Feature;

use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class CliffordTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        config(['app.key' => 'base64:'.base64_encode(str_repeat('k', 32)),
            'session.secure' => false, 'clifford.backend_url' => 'http://127.0.0.1:8000',
            'clifford.backend_token' => str_repeat('x', 40),
            'clifford.password_hash' => Hash::make('a-long-test-password')]);
        Http::preventStrayRequests();
    }

    public function test_guest_cannot_access_console_or_proxy(): void
    {
        $this->get('/')->assertRedirect('/login');
        $this->getJson('/api/providers')->assertUnauthorized();
        $this->postJson('/api/chat/stream', ['text' => 'Hello'])->assertUnauthorized();
        $this->postJson('/api/voice/ticket')->assertUnauthorized();
        Http::assertNothingSent();
    }

    public function test_login_and_logout_use_private_session(): void
    {
        $this->post('/login', ['password' => 'incorrect'])->assertSessionHasErrors('password');
        $this->get('/')->assertRedirect('/login');
        $this->post('/login', ['password' => 'a-long-test-password'])->assertRedirect('/')
            ->assertSessionHas('clifford_authenticated', true);
        $this->get('/')->assertOk()->assertSee('CLIFFORD')->assertDontSee(str_repeat('x', 40));
        $this->post('/logout')->assertRedirect('/login')->assertSessionMissing('clifford_authenticated');
    }

    public function test_unconfigured_owner_fails_closed(): void
    {
        config(['clifford.password_hash' => '']);
        $this->post('/login', ['password' => 'a-long-test-password'])->assertSessionHasErrors('password');
        $this->getJson('/api/providers')->assertUnauthorized();
    }

    public function test_provider_proxy_keeps_backend_token_server_side(): void
    {
        Http::fake(['127.0.0.1:8000/v1/providers' => Http::response([
            'model' => 'gemma3:12b', 'assistant_name' => 'Clifford', 'wake_phrase' => 'Clifford',
            'backend_token' => 'must-not-be-forwarded',
        ])]);
        $this->withSession(['clifford_authenticated' => true])->getJson('/api/providers')
            ->assertOk()->assertJsonPath('model', 'gemma3:12b')
            ->assertDontSee('must-not-be-forwarded')->assertDontSee(str_repeat('x', 40));
        Http::assertSent(fn ($request) => $request->hasHeader('Authorization', 'Bearer '.str_repeat('x', 40)));
    }

    public function test_sse_proxy_returns_real_upstream_frames(): void
    {
        $frames = "event: assistant.delta\ndata: {\"type\":\"assistant.delta\",\"payload\":{\"text\":\"Hello\"}}\n\n";
        Http::fake(['127.0.0.1:8000/v1/chat/stream' => Http::response($frames, 200,
            ['Content-Type' => 'text/event-stream'])]);
        $response = $this->withSession(['clifford_authenticated' => true])
            ->postJson('/api/chat/stream', ['text' => 'Hello']);
        $response->assertOk()->assertHeader('Content-Type', 'text/event-stream; charset=UTF-8')
            ->assertHeader('X-Accel-Buffering', 'no');
        $this->assertSame($frames, $response->streamedContent());
        Http::assertSent(fn ($request) => $request['text'] === 'Hello');
    }

    public function test_invalid_input_never_reaches_kernel(): void
    {
        $this->withSession(['clifford_authenticated' => true])
            ->postJson('/api/chat/stream', ['text' => '', 'session_id' => '../../etc/passwd'])
            ->assertUnprocessable();
        Http::assertNothingSent();
    }

    public function test_backend_error_is_redacted(): void
    {
        Http::fake(['127.0.0.1:8000/*' => Http::response('private-token-value', 401)]);
        $this->withSession(['clifford_authenticated' => true])
            ->getJson('/api/providers')->assertStatus(502)->assertDontSee('private-token-value');
    }

    public function test_voice_proxy_returns_scoped_ticket_only(): void
    {
        Http::fake(['127.0.0.1:8000/v1/voice/tickets' => Http::response(['ticket' => 'one-use-ticket',
            'expires_in' => 30, 'private' => 'do-not-forward'])]);
        $this->withSession(['clifford_authenticated' => true])->postJson('/api/voice/ticket')
            ->assertOk()->assertJsonPath('websocket_path', '/clifford-voice')
            ->assertJsonPath('ticket', 'one-use-ticket')->assertDontSee('do-not-forward')
            ->assertDontSee(str_repeat('x', 40));
    }

    public function test_non_local_plain_http_backend_is_rejected(): void
    {
        config(['clifford.backend_url' => 'http://example.com']);
        $this->withSession(['clifford_authenticated' => true])->getJson('/api/providers')
            ->assertStatus(503)->assertJsonPath('error.code', 'remote_backend_requires_https');
        Http::assertNothingSent();
    }

    public function test_interactive_installer_hashes_password_and_preserves_existing_settings(): void
    {
        $directory = sys_get_temp_dir().'/clifford-env-'.bin2hex(random_bytes(8));
        mkdir($directory, 0700);
        $path = $directory.'/.env';
        file_put_contents($path, "APP_KEY=keep-existing-key\nUNRELATED_SETTING=preserve-me\n");
        $this->app->useEnvironmentPath($directory);
        $this->app->loadEnvironmentFrom('.env');
        try {
            $this->artisan('clifford:install')
                ->expectsQuestion('Public HTTPS URL', 'https://clifford.parsabe.com')
                ->expectsQuestion('Private kernel URL', 'http://127.0.0.1:8000')
                ->expectsQuestion('Kernel CLIFFORD_AUTH_SECRET (input stays hidden)', str_repeat('t', 43))
                ->expectsQuestion('Choose a web login password (12–72 bytes)', 'a-private-test-password')
                ->expectsQuestion('Repeat the web login password', 'a-private-test-password')
                ->assertSuccessful();
            $contents = file_get_contents($path);
            $this->assertStringContainsString('UNRELATED_SETTING=preserve-me', $contents);
            $this->assertStringContainsString('APP_KEY=keep-existing-key', $contents);
            $this->assertStringNotContainsString('a-private-test-password', $contents);
            preg_match("/CLIFFORD_WEB_PASSWORD_HASH='([^']+)'/", $contents, $matches);
            $this->assertTrue(Hash::check('a-private-test-password', $matches[1]));
            $this->assertSame(0600, fileperms($path) & 0777);
        } finally {
            unlink($path);
            rmdir($directory);
        }
    }

    public function test_invalid_backend_metadata_is_not_forwarded(): void
    {
        Http::fake(['127.0.0.1:8000/v1/providers' => Http::response('not json', 200)]);
        $this->withSession(['clifford_authenticated' => true])->getJson('/api/providers')
            ->assertStatus(502)->assertJsonPath('error.code', 'invalid_backend_response');
    }
}
