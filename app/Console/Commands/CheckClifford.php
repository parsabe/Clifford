<?php

namespace App\Console\Commands;

use App\Services\KernelClient;
use Illuminate\Console\Command;
use RuntimeException;

class CheckClifford extends Command
{
    protected $signature = 'clifford:check';

    protected $description = 'Check local kernel socket and model availability without access tokens';

    public function handle(KernelClient $kernel): int
    {
        if (! config('app.key')) {
            $this->error('Run php artisan clifford:install first.');

            return self::FAILURE;
        }
        try {
            $providers = $kernel->request('GET', '/v1/providers');
            $check = $kernel->request('GET', '/v1/providers/check');
            if (! $providers->successful() || ! $check->successful()) {
                $this->error('Private kernel socket request failed.');

                return self::FAILURE;
            }
            if (! $check->json('reachable') || ! $check->json('model_installed')) {
                $this->error('Ollama/model not ready. Complete the kernel installation.');

                return self::FAILURE;
            }
            if (! $providers->json('speech.model_installed')) {
                $this->error('Vosk model is missing. Complete the kernel speech-model installation.');

                return self::FAILURE;
            }
            $this->info('Private socket, model and speech files are available.');
            $this->line('Verify aaPanel access protection, HTTPS and physical voice behavior in the browser.');

            return self::SUCCESS;
        } catch (RuntimeException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        }
    }
}
