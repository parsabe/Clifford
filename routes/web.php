<?php

use App\Http\Controllers\CliffordController;
use App\Http\Controllers\LoginController;
use App\Http\Middleware\CliffordAuthenticated;
use Illuminate\Support\Facades\Route;

Route::get('/login', [LoginController::class, 'show'])->name('login');
Route::post('/login', [LoginController::class, 'login'])->middleware('throttle:6,1');
Route::middleware(CliffordAuthenticated::class)->group(function () {
    Route::view('/', 'console')->name('console');
    Route::redirect('/console', '/');
    Route::post('/logout', [LoginController::class, 'logout'])->name('logout');
    Route::get('/api/providers', [CliffordController::class, 'providers'])->middleware('throttle:60,1');
    Route::post('/api/chat/stream', [CliffordController::class, 'stream'])->middleware('throttle:30,1');
    Route::post('/api/voice/ticket', [CliffordController::class, 'voiceTicket'])->middleware('throttle:20,1');
});
