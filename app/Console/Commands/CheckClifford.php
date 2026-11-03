<?php

namespace App\Console\Commands;

use App\Services\KernelClient;
use Illuminate\Console\Command;
use RuntimeException;

class CheckClifford extends Command
{
    protected $signature = 'clifford:check';

    protected $description = 'Check private web configuration and live kernel/model availability';

    public function handle(KernelClient $kernel): int
    {
        if (! config('app.key') || ! config('clifford.password_hash')) {
            $this->error('Run php artisan clifford:install first.');

            return self::FAILURE;
        }
        if (! filter_var(ini_get('allow_url_fopen'), FILTER_VALIDATE_BOOL)) {
            $this->error('Enable allow_url_fopen for PHP HTTP response streaming.');

            return self::FAILURE;
        }
        try {
            $providers = $kernel->request('GET', '/v1/providers');
            $check = $kernel->request('GET', '/v1/providers/check');
            if (! $providers->successful() || ! $check->successful()) {
                $this->error('Kernel authentication or health check failed. Check private URL/token.');

                return self::FAILURE;
            }
            $this->info('Kernel authenticated; model: '.($providers->json('model') ?: 'unknown'));
            if (! $check->json('reachable') || ! $check->json('model_installed')) {
                $this->error('Ollama/model not ready. Complete the kernel model installation.');

                return self::FAILURE;
            }
            if (! $providers->json('speech.model_installed')) {
                $this->error('Vosk model is missing. Complete kernel speech-model installation.');

                return self::FAILURE;
            }
            $this->info('Model and speech files are present. Test live chat and microphone in the browser.');
            $this->line('HTTPS and the aaPanel voice WebSocket location still need browser verification.');

            return self::SUCCESS;
        } catch (RuntimeException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        }
    }
}
