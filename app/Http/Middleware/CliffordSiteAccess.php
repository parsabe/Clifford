<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class CliffordSiteAccess
{
    public function handle(Request $request, Closure $next)
    {
        // Local development only. Production always uses the aaPanel/Nginx perimeter.
        if (app()->environment('local') && in_array($request->ip(), ['127.0.0.1', '::1'], true)
            && in_array($request->getHost(), ['localhost', '127.0.0.1', '::1'], true)) {
            return $next($request);
        }
        // These are FastCGI server parameters, never client-supplied HTTP headers.
        if ($request->server('CLIFFORD_SITE_PROTECTED') !== '1') {
            abort(503, 'Enable aaPanel site password access and the supplied PHP-FPM parameters.');
        }
        if (! is_string($request->server('REMOTE_USER')) || $request->server('REMOTE_USER') === '') {
            abort(401, 'Site access protection did not authenticate this request.');
        }

        return $next($request);
    }
}
