<?php

namespace App\Console\Commands;

use Dotenv\Dotenv;
use Illuminate\Console\Command;

class InstallClifford extends Command
{
    protected $signature = 'clifford:install';

    protected $description = 'Initialize Laravel and remove retired custom authentication settings';

    public function handle(): int
    {
        $path = $this->laravel->environmentFilePath();
        if (! is_file($path)) {
            copy(base_path('.env.example'), $path);
        }
        $contents = file_get_contents($path);
        foreach (['CLIFFORD_BACKEND_TOKEN', 'CLIFFORD_BACKEND_TIMEOUT', 'CLIFFORD_WEB_PASSWORD_HASH',
            'CLIFFORD_BACKEND_URL', 'CLIFFORD_AUTH_SECRET'] as $retired) {
            $contents = preg_replace('/^'.preg_quote($retired, '/').'=.*\R?/m', '', $contents);
        }
        $contents = preg_replace('/^# Set interactively with php artisan clifford:install\..*\R?/m', '', $contents);
        if (! preg_match('/^CLIFFORD_SOCKET_PATH=/m', $contents)) {
            $contents = rtrim($contents)."\nCLIFFORD_SOCKET_PATH=/run/clifford/api.sock\n";
        }
        file_put_contents($path, $contents, LOCK_EX);
        chmod($path, 0600);
        $this->call('config:clear');
        $environmentValues = Dotenv::parse($contents);
        if (empty($environmentValues['APP_KEY'])) {
            if (! array_key_exists('APP_KEY', $environmentValues)) {
                file_put_contents($path, rtrim($contents)."\nAPP_KEY=\n", LOCK_EX);
            }
            // A stale config cache must not make key:generate search for the old key in this file.
            config(['app.key' => '']);
            if ($this->call('key:generate', ['--force' => true]) !== self::SUCCESS) {
                return self::FAILURE;
            }
        }
        $this->info('Laravel initialized. No backend token or custom web password is required.');
        $this->line('Use aaPanel site password access and the supplied FastCGI parameters.');
        $this->line('The kernel connects through /run/clifford/api.sock.');

        return self::SUCCESS;
    }
}
