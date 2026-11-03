<?php

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use RuntimeException;

class KernelClient
{
    // Internal bounds, not settings the site owner needs to fill in.
    public const REQUEST_TIMEOUT = 240;

    public function assertAvailable(): string
    {
        $path = config('clifford.socket_path');
        if (! extension_loaded('curl')) {
            throw new RuntimeException('php_curl_required');
        }
        if (! is_string($path) || ! str_starts_with($path, '/') || str_contains($path, "\0")) {
            throw new RuntimeException('invalid_kernel_socket');
        }
        clearstatcache(true, $path);
        if (@filetype($path) !== 'socket' || ! is_readable($path)) {
            throw new RuntimeException('kernel_socket_unavailable');
        }

        return $path;
    }

    public function request(string $method, string $path, array $body = [])
    {
        $socket = $this->assertAvailable();
        try {
            return Http::acceptJson()->connectTimeout(5)->timeout(self::REQUEST_TIMEOUT)
                ->withOptions(['allow_redirects' => false,
                    'proxy' => '', 'curl' => [CURLOPT_UNIX_SOCKET_PATH => $socket]])
                ->send($method, 'http://localhost'.$path, $method === 'GET' ? [] : ['json' => $body]);
        } catch (ConnectionException $exception) {
            throw new RuntimeException('kernel_socket_unavailable');
        }
    }

    public function stream(string $path, array $body, callable $onChunk): void
    {
        $socket = $this->assertAvailable();
        $status = 0;
        $handle = curl_init('http://localhost'.$path);
        curl_setopt_array($handle, [
            CURLOPT_UNIX_SOCKET_PATH => $socket,
            CURLOPT_PROXY => '',
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($body, JSON_THROW_ON_ERROR),
            CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Accept: text/event-stream'],
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => self::REQUEST_TIMEOUT,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_HEADERFUNCTION => function ($handle, string $header) use (&$status) {
                if (preg_match('/^HTTP\/\S+\s+(\d{3})/', $header, $matches)) {
                    $status = (int) $matches[1];
                }

                return strlen($header);
            },
            CURLOPT_WRITEFUNCTION => function ($handle, string $chunk) use (&$status, $onChunk) {
                if (connection_aborted()) {
                    return 0;
                }
                if ($status >= 200 && $status < 300) {
                    $onChunk($chunk);
                }

                return strlen($chunk);
            },
        ]);
        try {
            $result = curl_exec($handle);
            if (! connection_aborted() && ($result === false || $status < 200 || $status >= 300)) {
                throw new RuntimeException('kernel_stream_unavailable');
            }
        } finally {
            curl_close($handle);
        }
    }
}
