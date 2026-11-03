<?php

return [
    'backend_url' => env('CLIFFORD_BACKEND_URL', 'http://127.0.0.1:8000'),
    'backend_token' => env('CLIFFORD_BACKEND_TOKEN', ''),
    'password_hash' => env('CLIFFORD_WEB_PASSWORD_HASH', ''),
    'timeout' => (int) env('CLIFFORD_BACKEND_TIMEOUT', 240),
    'voice_path' => '/clifford-voice',
];
