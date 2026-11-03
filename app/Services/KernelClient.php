<?php

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use RuntimeException;

class KernelClient
{
    public function request(string $method, string $path, array $body = [], bool $stream = false)
    {
        $url = rtrim((string) config('clifford.backend_url'), '/');
        $parts = parse_url($url);
        if (! $parts || ! in_array($parts['scheme'] ?? '', ['http', 'https'], true)
            || isset($parts['user']) || isset($parts['pass']) || isset($parts['query']) || isset($parts['fragment'])) {
            throw new RuntimeException('backend_not_configured');
        }
        if (($parts['scheme'] ?? '') === 'http'
            && ! in_array($parts['host'] ?? '', ['127.0.0.1', 'localhost', '::1'], true)) {
            throw new RuntimeException('remote_backend_requires_https');
        }
        $token = config('clifford.backend_token');
        if (! is_string($token) || strlen($token) < 32) {
            throw new RuntimeException('backend_not_configured');
        }
        try {
            return Http::withToken($token)->accept($stream ? 'text/event-stream' : 'application/json')
                ->connectTimeout(5)->timeout(config('clifford.timeout'))
                ->withOptions(['stream' => $stream, 'allow_redirects' => false])
                ->send($method, $url.$path, $method === 'GET' ? [] : ['json' => $body]);
        } catch (ConnectionException $exception) {
            // Exception text can contain credentials, endpoint details or prompts.
            throw new RuntimeException('backend_unavailable');
        }
    }
}
