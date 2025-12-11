<?php
use App\Http\Controllers\HadithController;
use Illuminate\Support\Facades\Route;

// Info & Index (must be early to avoid conflicts)
Route::get('/', [HadithController::class, 'index']);
Route::get('/info', [HadithController::class, 'info']);

// Languages (no conflicts)
Route::get('/languages', [HadithController::class, 'languages']);

// Random (no conflicts)
Route::get('/random', [HadithController::class, 'random']);

// Search - specific paths before variable paths
Route::get('/search', [HadithController::class, 'search']);
Route::get('/search/{term}', [HadithController::class, 'searchPath']);

// HadeethEnc API Compatible - specific hadeeths endpoints first
Route::get('/hadeeths/list', [HadithController::class, 'hadeethsList']);
Route::get('/hadeeths/one', [HadithController::class, 'hadeethOne']);
Route::get('/hadeeths', [HadithController::class, 'hadiths']); // Query string endpoint

// Categories - specific paths before variable paths
Route::get('/categories/list', [HadithController::class, 'categories']);
Route::get('/categories/roots', [HadithController::class, 'rootCategories']);
Route::get('/categories', [HadithController::class, 'categories']);
Route::get('/categories/{category}/children', [HadithController::class, 'categoryChildren']);
Route::get('/categories/{category}/hadeeths', [HadithController::class, 'categoryHadiths']); // Alias
Route::get('/categories/{category}/hadiths', [HadithController::class, 'categoryHadiths']);
Route::get('/categories/{category}', [HadithController::class, 'getCategory']);

// Books - specific paths before variable paths
Route::get('/books', [HadithController::class, 'books']);
Route::get('/books/{book}/chapters/{chapter}/hadiths/{hadith_number}/translations/{lang}', [HadithController::class, 'getHadithTranslation'])->name('hadith.chapter.translation');
Route::get('/books/{book}/chapters/{chapter}/hadeeths/{hadith_number}/translations/{lang}', [HadithController::class, 'getHadithTranslation']); // Alias
Route::get('/books/{book}/chapters/{chapter}/hadiths/{hadith_number}', [HadithController::class, 'getHadith']);
Route::get('/books/{book}/chapters/{chapter}/hadeeths/{hadith_number}', [HadithController::class, 'getHadith']); // Alias
Route::get('/books/{book}/chapters/{chapter}/hadeeths', [HadithController::class, 'chapterHadiths']); // Alias
Route::get('/books/{book}/chapters/{chapter}', [HadithController::class, 'chapterHadiths']);
Route::get('/books/{book}/chapters', [HadithController::class, 'bookChapters']);
Route::get('/books/{book}/hadiths/{hadith_number}/translations/{lang}', [HadithController::class, 'getHadithTranslation'])->name('hadith.translation');
Route::get('/books/{book}/hadeeths/{hadith_number}/translations/{lang}', [HadithController::class, 'getHadithTranslation']); // Alias
Route::get('/books/{book}/hadiths/{hadith_number}', [HadithController::class, 'getHadith']);
Route::get('/books/{book}/hadeeths/{hadith_number}', [HadithController::class, 'getHadith']); // Alias
Route::get('/books/{book}', [HadithController::class, 'getBook']);

// Chapters - specific paths before variable paths
Route::get('/chapters', [HadithController::class, 'chapters']);
Route::get('/chapters/{chapter}/hadeeths', [HadithController::class, 'chapterHadithsById']); // Alias
Route::get('/chapters/{chapter}/hadiths', [HadithController::class, 'chapterHadithsById']);
Route::get('/chapters/{chapter}', [HadithController::class, 'getChapter']);

// Individual hadiths by ID - put after specific paths
Route::get('/hadeeths/{id}/translations/{lang}', [HadithController::class, 'getHadithTranslationById']); // Alias
Route::get('/hadiths/{id}/translations/{lang}', [HadithController::class, 'getHadithTranslationById']);
Route::get('/hadeeths/{id}', [HadithController::class, 'getHadithById']); // Alias
Route::get('/hadiths/{id}', [HadithController::class, 'getHadithById']);

// Topics
Route::get('/topics/{topic}/hadeeths', [HadithController::class, 'topicHadiths']); // Alias
Route::get('/topics/{topic}/hadiths', [HadithController::class, 'topicHadiths']);

// Collection/Chapter shortcut route - must be last
Route::get('/{collection}/{chapter}', [HadithController::class, 'collectionChapterHadiths']);

// Admin - trigger sync for missing translations (restrict in production)
// Admin sync - restricted in production. Protect with auth middleware.
Route::post('/admin/sync-missing-translations', [HadithController::class, 'syncMissingTranslations'])
	->middleware(['auth:api']);