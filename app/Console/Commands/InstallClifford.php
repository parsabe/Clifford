<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Hash;

class InstallClifford extends Command
{
    protected $signature = 'clifford:install';

    protected $description = 'Configure private backend access and the web owner password interactively';

    public function handle(): int
    {
        $environment = $this->laravel->environmentFilePath();
        if (! is_file($environment)) {
            copy(base_path('.env.example'), $environment);
            chmod($environment, 0600);
        }
        $url = $this->ask('Public HTTPS URL', 'https://clifford.parsabe.com');
        $backend = $this->ask('Private kernel URL', 'http://127.0.0.1:8000');
        if (! filter_var($url, FILTER_VALIDATE_URL) || ! str_starts_with($url, 'https://')
            || ! filter_var($backend, FILTER_VALIDATE_URL)) {
            $this->error('Use a valid public HTTPS URL and private backend URL.');

            return self::FAILURE;
        }
        $token = $this->secret('Kernel CLIFFORD_AUTH_SECRET (input stays hidden)');
        if (! is_string($token) || ! preg_match('/^[A-Za-z0-9_-]{32,256}$/', $token)) {
            $this->error('Use the generated kernel token, with at least 32 URL-safe characters.');

            return self::FAILURE;
        }
        $password = $this->secret('Choose a web login password (12–72 bytes)');
        $confirmation = $this->secret('Repeat the web login password');
        if (! is_string($password) || strlen($password) < 12 || strlen($password) > 72
            || ! hash_equals($password, (string) $confirmation)) {
            $this->error('Passwords must match and contain 12–72 bytes.');

            return self::FAILURE;
        }
        $values = [
            'APP_NAME' => 'Clifford', 'APP_ENV' => 'production', 'APP_DEBUG' => 'false',
            'APP_URL' => rtrim($url, '/'), 'SESSION_DRIVER' => 'file', 'SESSION_SECURE_COOKIE' => 'true',
            'CACHE_STORE' => 'file', 'QUEUE_CONNECTION' => 'sync',
            'CLIFFORD_BACKEND_URL' => rtrim($backend, '/'), 'CLIFFORD_BACKEND_TOKEN' => $token,
            'CLIFFORD_WEB_PASSWORD_HASH' => Hash::make($password),
        ];
        $contents = file_get_contents($environment);
        foreach ($values as $key => $value) {
            if (str_contains($value, "'") || preg_match('/[\r\n\x00]/', $value)) {
                $this->error('Configuration values cannot contain quotes or line breaks.');

                return self::FAILURE;
            }
            $line = $key."='".$value."'";
            $pattern = '/^'.preg_quote($key, '/').'=.*/m';
            $contents = preg_match($pattern, $contents)
                ? preg_replace_callback($pattern, fn () => $line, $contents)
                : rtrim($contents)."\n".$line."\n";
        }
        file_put_contents($environment, $contents, LOCK_EX);
        chmod($environment, 0600);
        $this->call('config:clear');
        if (! config('app.key')) {
            $this->call('key:generate', ['--force' => true]);
        }
        $this->info('Saved private configuration. No credentials were printed.');
        $this->info('Set aaPanel document root to this application\'s public/ directory.');

        return self::SUCCESS;
    }
}
