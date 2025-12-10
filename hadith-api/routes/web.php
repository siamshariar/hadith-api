<?php

use App\Http\Controllers\HadithController;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider and all of them will
| be assigned to the "web" middleware group. Make something great!
|
*/

// Basic welcome route
Route::get('/', function () {
    return response()->json([
        'message' => 'Hadith API Server is running!',
        'version' => '1.0.0',
        'timestamp' => now(),
        'endpoints' => [
            'api' => '/api/',
            'web_interface' => '/hadith',
            'books' => '/hadith/books'
        ]
    ]);
});

// Web Interface Routes
Route::get('/hadith', [HadithController::class, 'simpleWelcome']);
Route::get('/hadith/books', [HadithController::class, 'simpleBooks']);
Route::get('/hadith/books/{id}', [HadithController::class, 'simpleBookShow']);

// Test route
Route::get('/test', function () {
    return response()->json([
        'status' => 'working',
        'message' => 'Laravel is running correctly!',
        'time' => now(),
        'controller' => 'HadithController exists and is working'
    ]);
});