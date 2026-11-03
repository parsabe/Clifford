<?php

namespace App\Http\Controllers;

use App\Services\KernelClient;
use Illuminate\Http\Request;
use RuntimeException;
use Throwable;

class CliffordController extends Controller
{
    public function providers(KernelClient $kernel)
    {
        try {
            $response = $kernel->request('GET', '/v1/providers');
            if (! $response->successful()) {
                return response()->json(['error' => ['code' => 'backend_unavailable']], 502);
            }

            $metadata = $response->json();
            if (! is_array($metadata) || ! is_string($metadata['assistant_name'] ?? null)
                || ! is_string($metadata['wake_phrase'] ?? null)) {
                return response()->json(['error' => ['code' => 'invalid_backend_response']], 502);
            }

            // Explicitly select non-secret presentation metadata.
            return response()->json(collect($metadata)->only([
                'selected', 'model', 'assistant_name', 'wake_phrase', 'speech',
            ])->all());
        } catch (RuntimeException $exception) {
            return response()->json(['error' => ['code' => $exception->getMessage()]], 503);
        }
    }

    public function voiceTicket(KernelClient $kernel)
    {
        try {
            $response = $kernel->request('POST', '/v1/voice/tickets');
            $ticket = $response->json('ticket');
            if (! $response->successful() || ! is_string($ticket) || strlen($ticket) > 128) {
                return response()->json(['error' => ['code' => 'voice_ticket_unavailable']], 502);
            }

            return response()->json(['ticket' => $ticket, 'expires_in' => 30,
                'websocket_path' => config('clifford.voice_path')])->header('Cache-Control', 'no-store');
        } catch (RuntimeException $exception) {
            return response()->json(['error' => ['code' => $exception->getMessage()]], 503);
        }
    }

    public function stream(Request $request, KernelClient $kernel)
    {
        $data = $request->validate([
            'text' => ['required', 'string', 'max:12000'],
            'session_id' => ['nullable', 'uuid'],
            'mode' => ['sometimes', 'in:fast,balanced,deep,agentic'],
        ]);
        try {
            $upstream = $kernel->request('POST', '/v1/chat/stream', $data, true);
            if (! $upstream->successful()) {
                $upstream->toPsrResponse()->getBody()->close();

                return response()->json(['error' => ['code' => 'backend_unavailable']], 502);
            }
        } catch (RuntimeException $exception) {
            return response()->json(['error' => ['code' => $exception->getMessage()]], 503);
        }

        return response()->stream(function () use ($upstream) {
            $body = $upstream->toPsrResponse()->getBody();
            try {
                // Release PHP's session lock before the long-lived response.
                // Laravel saves sessions in middleware before this callback is sent.
                if (function_exists('set_time_limit')) {
                    set_time_limit(config('clifford.timeout') + 10);
                }
                while (! $body->eof() && ! connection_aborted()) {
                    echo $body->read(1024);
                    if (ob_get_level() > 0) {
                        ob_flush();
                    }
                    flush();
                }
            } catch (Throwable $exception) {
                echo "event: error\ndata: ".json_encode([
                    'type' => 'error', 'payload' => ['code' => 'stream_interrupted'],
                ])."\n\n";
            } finally {
                $body->close();
            }
        }, 200, ['Content-Type' => 'text/event-stream', 'Cache-Control' => 'no-cache, no-store',
            'X-Accel-Buffering' => 'no']);
    }
}
