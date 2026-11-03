<?php

use App\Http\Controllers\CliffordController;
use App\Http\Middleware\CliffordSiteAccess;
use Illuminate\Support\Facades\Route;

Route::middleware(CliffordSiteAccess::class)->group(function () {
    Route::view('/', 'console')->name('console');
    Route::redirect('/console', '/');
    Route::get('/api/providers', [CliffordController::class, 'providers'])->middleware('throttle:60,1');
    Route::post('/api/chat/stream', [CliffordController::class, 'stream'])->middleware('throttle:30,1');
    Route::post('/api/voice/ticket', [CliffordController::class, 'voiceTicket'])->middleware('throttle:20,1');
});
