<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;

class LoginController extends Controller
{
    public function show()
    {
        return view('login');
    }

    public function login(Request $request)
    {
        $data = $request->validate(['password' => ['required', 'string', 'max:1024']]);
        $hash = config('clifford.password_hash');
        if (! is_string($hash) || $hash === '') {
            return back()->withErrors(['password' => 'Run php artisan clifford:install on the server first.']);
        }
        if (! Hash::check($data['password'], $hash)) {
            // Never flash the submitted password or include it in a response.
            return back()->withErrors(['password' => 'The password is incorrect.']);
        }
        $request->session()->regenerate();
        $request->session()->put('clifford_authenticated', true);

        return redirect()->route('console');
    }

    public function logout(Request $request)
    {
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect()->route('login');
    }
}
