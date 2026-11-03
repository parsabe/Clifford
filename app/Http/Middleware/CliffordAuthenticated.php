<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class CliffordAuthenticated
{
    public function handle(Request $request, Closure $next)
    {
        if (! $request->session()->get('clifford_authenticated')) {
            return $request->expectsJson()
                ? response()->json(['error' => ['code' => 'unauthenticated']], 401)
                : redirect()->route('login');
        }

        return $next($request);
    }
}
