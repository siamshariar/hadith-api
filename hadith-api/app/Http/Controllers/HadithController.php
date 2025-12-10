<?php

namespace App\Http\Controllers;

use App\Models\Book;
use App\Models\Chapter;
use App\Models\Hadith;
use App\Models\Category;
use App\Models\HadithTranslation;
use App\Models\HadithReferenceTranslation;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class HadithController extends Controller
{
    // Common response format methods
    private function successResponse($data, $meta = [], $status = 200): JsonResponse
    {
        return response()->json([
            'success' => true,
            'data' => $data,
            'meta' => $meta
        ], $status, [], JSON_UNESCAPED_UNICODE);
    }

    private function errorResponse($message, $error = null, $status = 500): JsonResponse
    {
        $response = [
            'success' => false,
            'message' => $message
        ];
        
        if ($error && config('app.debug')) {
            $response['error'] = $error;
        }
        
        return response()->json($response, $status);
    }

    private function notFoundResponse($message = 'Resource not found'): JsonResponse
    {
        return $this->errorResponse($message, null, 404);
    }

    // Helper method to find book by various identifiers
    private function findBook($identifier): ?Book
    {
        try {
            // First check if identifier is numeric (could be ID)
            if (is_numeric($identifier)) {
                $book = Book::where('id', $identifier)->first();
                if ($book) return $book;
            }

            // Try by code
            $book = Book::where('code', $identifier)->first();
            if ($book) return $book;

            // Try by name (partial match)
            $book = Book::where('name_en', 'LIKE', "%{$identifier}%")
                ->orWhere('name_ar', 'LIKE', "%{$identifier}%")
                ->first();
            
            if ($book) return $book;

            // Try common variations
            $variations = [
                'bukhari' => ['bukhari', 'sahih bukhari', 'صحيح البخاري', 'بخاری'],
                'muslim' => ['muslim', 'sahih muslim', 'صحيح مسلم', 'مسلم'],
                'abu-dawud' => ['abu-dawud', 'abudawud', 'سنن أبي داود', 'ابو داود'],
                'tirmidhi' => ['tirmidhi', 'tirmizi', 'سنن الترمذي', 'ترمذی'],
                'nasai' => ['nasai', 'nasa\'i', 'سنن النسائي', 'نسائی'],
                'ibn-majah' => ['ibn-majah', 'ibnmajah', 'سنن ابن ماجه', 'ابن ماجه'],
                'ahmad' => ['ahmad', 'musnad ahmad', 'مسند أحمد', 'احمد'],
                'malik' => ['malik', 'muwatta malik', 'موطأ مالك', 'مالک'],
            ];

            foreach ($variations as $code => $options) {
                if (in_array(strtolower($identifier), $options)) {
                    return Book::where('code', $code)->first();
                }
            }

            return null;
        } catch (\Exception $e) {
            Log::error("Error finding book: {$identifier}", ['error' => $e->getMessage()]);
            return null;
        }
    }

    // Helper method to find chapter
    private function findChapter($bookId, $chapterIdentifier): ?Chapter
    {
        try {
            // Check if identifier is numeric (chapter_no)
            if (is_numeric($chapterIdentifier)) {
                return Chapter::where('book_id', $bookId)
                    ->where('chapter_no', $chapterIdentifier)
                    ->first();
            } else {
                return Chapter::where('book_id', $bookId)
                    ->where('name_en', 'LIKE', "%{$chapterIdentifier}%")
                    ->orWhere('name_ar', 'LIKE', "%{$chapterIdentifier}%")
                    ->first();
            }
        } catch (\Exception $e) {
            Log::error("Error finding chapter: {$chapterIdentifier}", ['error' => $e->getMessage()]);
            return null;
        }
    }

    // Helper method to localize numbers
    private function localizeNumbers($text, $languageCode): string
    {
        if (empty($text)) return '';
        
        $numeralMaps = [
            'bn' => ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'],
            'ur' => ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'],
            'ar' => ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'],
            'fa' => ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'],
            'hi' => ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९'],
        ];

        if (!isset($numeralMaps[$languageCode])) {
            return $text;
        }

        $targetNumerals = $numeralMaps[$languageCode];
        $result = $text;

        for ($i = 0; $i < 10; $i++) {
            $result = str_replace((string)$i, $targetNumerals[$i], $result);
        }

        return $result;
    }

    /**
     * API Information
     */
    public function info(): JsonResponse
    {
        try {
            $stats = [
                'books' => Book::count(),
                'chapters' => Chapter::count(),
                'hadiths' => Hadith::count(),
                'translations' => HadithTranslation::distinct('localization_code')->count('localization_code'),
                'categories' => Category::count()
            ];

            $endpoints = [
                'GET /' => 'API Information',
                'GET /info' => 'Detailed API Information',
                'GET /books' => 'List all books',
                'GET /books/{book}' => 'Get specific book',
                'GET /books/{book}/chapters' => 'Get book chapters',
                'GET /books/{book}/chapters/{chapter}' => 'Get chapter hadiths',
                'GET /books/{book}/chapters/{chapter}/hadiths/{hadith_number}' => 'Get specific hadith',
                'GET /chapters' => 'List all chapters',
                'GET /chapters/{chapter}' => 'Get chapter details',
                'GET /hadiths' => 'List hadiths (paginated)',
                'GET /hadiths/{id}' => 'Get hadith by ID',
                'GET /hadiths/{id}/translations/{lang}' => 'Get hadith translation',
                'GET /search' => 'Search hadiths (query: q)',
                'GET /search/{term}' => 'Search hadiths by term',
                'GET /random' => 'Get random hadith',
                'GET /languages' => 'Get supported languages',
                'GET /categories' => 'Get all categories',
                'GET /categories/{category}' => 'Get category details',
                'GET /categories/{category}/children' => 'Get category children',
                'GET /categories/{category}/hadiths' => 'Get category hadiths',
                'GET /categories/roots' => 'Get root categories',
                'GET /hadeeths/list' => 'HadeethEnc compatible: List hadiths',
                'GET /hadeeths/one' => 'HadeethEnc compatible: Get single hadith',
                'GET /topics/{topic}/hadiths' => 'Get hadiths by topic',
                'GET /{collection}/{chapter}' => 'Shortcut: Get hadiths by collection and chapter',
            ];

            return $this->successResponse([
                'name' => 'Hadith API',
                'version' => '1.0.0',
                'description' => 'Comprehensive Hadith database with multiple translations and API compatibility',
                'statistics' => $stats,
                'endpoints' => $endpoints,
                'defaults' => [
                    'language' => 'en',
                    'per_page' => 20,
                    'page' => 1
                ]
            ]);
        } catch (\Exception $e) {
            return $this->successResponse([
                'name' => 'Hadith API',
                'version' => '1.0.0',
                'description' => 'Comprehensive Hadith database',
                'note' => 'Database statistics unavailable',
                'endpoints' => [
                    'GET /' => 'API Information',
                    'GET /books' => 'List all books',
                    'GET /hadiths' => 'List hadiths',
                    'GET /search?q={query}' => 'Search hadiths',
                ]
            ]);
        }
    }

    /**
     * API Index
     */
    public function index(): JsonResponse
    {
        return $this->info();
    }

    /**
     * Get all books
     */
    public function books(Request $request): JsonResponse
    {
        try {
            $language = $request->query('language', 'en');
            $perPage = (int) $request->query('per_page', 20);
            $page = (int) $request->query('page', 1);

            $books = Book::orderBy('id')
                ->paginate($perPage, ['*'], 'page', $page);
            
            $formattedBooks = $books->map(function($book) use ($language) {
                return [
                    'id' => (string) $book->id,
                    'code' => $book->code,
                    'name' => $language === 'ar' && $book->name_ar ? $book->name_ar : $book->name_en,
                    'name_en' => $book->name_en,
                    'name_ar' => $book->name_ar,
                    'total_hadith' => (string) $book->total_hadith,
                    'total_chapters' => (string) $book->chapters()->count()
                ];
            });

            return $this->successResponse($formattedBooks, [
                'total' => $books->total(),
                'per_page' => $books->perPage(),
                'current_page' => $books->currentPage(),
                'last_page' => $books->lastPage()
            ]);

        } catch (\Exception $e) {
            Log::error('Books fetch error: ' . $e->getMessage());
            return $this->errorResponse('Failed to fetch books', $e->getMessage());
        }
    }

    /**
     * Get specific book
     */
    public function getBook($book): JsonResponse
    {
        try {
            $bookModel = $this->findBook($book);
            
            if (!$bookModel) {
                return $this->notFoundResponse('Book not found');
            }

            $language = request()->query('language', 'en');
            
            $bookData = [
                'id' => (string) $bookModel->id,
                'code' => $bookModel->code,
                'name' => $language === 'ar' && $bookModel->name_ar ? $bookModel->name_ar : $bookModel->name_en,
                'name_en' => $bookModel->name_en,
                'name_ar' => $bookModel->name_ar,
                'total_hadith' => (string) $bookModel->total_hadith,
                'total_chapters' => (string) $bookModel->chapters()->count(),
                'chapters' => $bookModel->chapters()
                    ->select('id', 'book_id', 'chapter_no', 'name_en', 'name_ar', 'total_hadith')
                    ->orderBy('chapter_no')
                    ->get()
                    ->map(function($chapter) use ($language) {
                        return [
                            'id' => (string) $chapter->id,
                            'chapter_no' => (string) $chapter->chapter_no,
                            'name' => $language === 'ar' && $chapter->name_ar ? $chapter->name_ar : $chapter->name_en,
                            'name_en' => $chapter->name_en,
                            'name_ar' => $chapter->name_ar,
                            'total_hadith' => (string) $chapter->total_hadith
                        ];
                    })
            ];

            return $this->successResponse($bookData);

        } catch (\Exception $e) {
            Log::error("Get book error: {$book}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch book', $e->getMessage());
        }
    }

    /**
     * Get book chapters
     */
    public function bookChapters($book): JsonResponse
    {
        try {
            $bookModel = $this->findBook($book);
            
            if (!$bookModel) {
                return $this->notFoundResponse('Book not found');
            }

            $language = request()->query('language', 'en');
            $perPage = (int) request()->query('per_page', 50);
            $page = (int) request()->query('page', 1);

            $chapters = Chapter::where('book_id', $bookModel->id)
                ->select('id', 'book_id', 'chapter_no', 'name_en', 'name_ar', 'total_hadith')
                ->orderBy('chapter_no')
                ->paginate($perPage, ['*'], 'page', $page);

            $formattedChapters = $chapters->map(function($chapter) use ($language) {
                return [
                    'id' => (string) $chapter->id,
                    'book_id' => (string) $chapter->book_id,
                    'chapter_no' => (string) $chapter->chapter_no,
                    'name' => $language === 'ar' && $chapter->name_ar ? $chapter->name_ar : $chapter->name_en,
                    'name_en' => $chapter->name_en,
                    'name_ar' => $chapter->name_ar,
                    'total_hadith' => (string) $chapter->total_hadith
                ];
            });

            return $this->successResponse($formattedChapters, [
                'book' => [
                    'id' => $bookModel->id,
                    'code' => $bookModel->code,
                    'name' => $language === 'ar' && $bookModel->name_ar ? $bookModel->name_ar : $bookModel->name_en
                ],
                'total' => $chapters->total(),
                'per_page' => $chapters->perPage(),
                'current_page' => $chapters->currentPage(),
                'last_page' => $chapters->lastPage()
            ]);

        } catch (\Exception $e) {
            Log::error("Book chapters error: {$book}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch book chapters', $e->getMessage());
        }
    }

    /**
     * Get chapter hadiths
     */
    public function chapterHadiths(Request $request, $book, $chapter): JsonResponse
    {
        try {
            $language = $request->query('language', 'en');
            $perPage = (int) $request->query('per_page', 20);
            $page = (int) $request->query('page', 1);

            $bookModel = $this->findBook($book);
            if (!$bookModel) {
                return $this->notFoundResponse('Book not found');
            }

            $chapterModel = $this->findChapter($bookModel->id, $chapter);
            if (!$chapterModel) {
                return $this->notFoundResponse('Chapter not found');
            }

            $hadiths = Hadith::where('book_id', $bookModel->id)
                ->where('chapter_id', $chapterModel->id)
                ->select('id', 'book_id', 'chapter_id', 'hadith_number', 'arabic_text', 'grade', 'references')
                ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar'])
                ->with(['translations' => function($q) use ($language) {
                    $q->where('localization_code', $language)
                      ->select('id', 'hadith_id', 'localization_code', 'translation_text', 'explanation', 'hints');
                }])
                ->orderBy('hadith_number')
                ->paginate($perPage, ['*'], 'page', $page);

            $formattedHadiths = $hadiths->map(function($hadith) use ($language) {
                $translation = $hadith->translations->first();
                
                // Try English translation as fallback
                if (!$translation && $language !== 'en') {
                    $translation = HadithTranslation::where('hadith_id', $hadith->id)
                        ->where('localization_code', 'en')
                        ->first();
                }

                return [
                    'id' => (string) $hadith->id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade,
                    'references' => $hadith->references,
                    'book' => [
                        'id' => $hadith->book->id,
                        'code' => $hadith->book->code,
                        'name' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                    ],
                    'chapter' => [
                        'id' => $hadith->chapter->id,
                        'chapter_no' => $hadith->chapter->chapter_no,
                        'name' => $language === 'ar' && $hadith->chapter->name_ar ? $hadith->chapter->name_ar : $hadith->chapter->name_en
                    ],
                    'translation' => $translation ? [
                        'language' => $translation->localization_code,
                        'text' => $this->localizeNumbers($translation->translation_text, $language),
                        'explanation' => $this->localizeNumbers($translation->explanation, $language),
                        'hints' => $translation->hints
                    ] : null
                ];
            });

            return $this->successResponse($formattedHadiths, [
                'book' => [
                    'id' => $bookModel->id,
                    'code' => $bookModel->code,
                    'name' => $language === 'ar' && $bookModel->name_ar ? $bookModel->name_ar : $bookModel->name_en
                ],
                'chapter' => [
                    'id' => $chapterModel->id,
                    'chapter_no' => $chapterModel->chapter_no,
                    'name' => $language === 'ar' && $chapterModel->name_ar ? $chapterModel->name_ar : $chapterModel->name_en
                ],
                'total' => $hadiths->total(),
                'per_page' => $hadiths->perPage(),
                'current_page' => $hadiths->currentPage(),
                'last_page' => $hadiths->lastPage()
            ]);

        } catch (\Exception $e) {
            Log::error("Chapter hadiths error: {$book}/{$chapter}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch chapter hadiths', $e->getMessage());
        }
    }

    /**
     * Collection/Chapter shortcut
     */
    public function collectionChapterHadiths(Request $request, $collection, $chapter): JsonResponse
    {
        // Reuse chapterHadiths logic
        return $this->chapterHadiths($request, $collection, $chapter);
    }

    /**
     * Get all hadiths (paginated)
     */
    public function hadiths(Request $request): JsonResponse
    {
        try {
            $language = $request->query('language', 'en');
            $perPage = (int) $request->query('per_page', 20);
            $page = (int) $request->query('page', 1);

            $hadiths = Hadith::select('id', 'book_id', 'chapter_id', 'hadith_number', 'arabic_text', 'grade', 'references')
                ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar'])
                ->orderBy('id')
                ->paginate($perPage, ['*'], 'page', $page);

            $formattedHadiths = $hadiths->map(function($hadith) use ($language) {
                return [
                    'id' => (string) $hadith->id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade,
                    'book' => [
                        'id' => $hadith->book->id,
                        'code' => $hadith->book->code,
                        'name' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                    ],
                    'chapter' => [
                        'id' => $hadith->chapter->id,
                        'chapter_no' => $hadith->chapter->chapter_no,
                        'name' => $language === 'ar' && $hadith->chapter->name_ar ? $hadith->chapter->name_ar : $hadith->chapter->name_en
                    ]
                ];
            });

            return $this->successResponse($formattedHadiths, [
                'total' => $hadiths->total(),
                'per_page' => $hadiths->perPage(),
                'current_page' => $hadiths->currentPage(),
                'last_page' => $hadiths->lastPage()
            ]);

        } catch (\Exception $e) {
            Log::error('Hadiths fetch error: ' . $e->getMessage());
            return $this->errorResponse('Failed to fetch hadiths', $e->getMessage());
        }
    }

    /**
     * Get all chapters
     */
    public function chapters(Request $request): JsonResponse
    {
        try {
            $language = $request->query('language', 'en');
            $perPage = (int) $request->query('per_page', 20);
            $page = (int) $request->query('page', 1);

            $chapters = Chapter::select('id', 'book_id', 'chapter_no', 'name_en', 'name_ar', 'total_hadith')
                ->with(['book:id,code,name_en,name_ar'])
                ->orderBy('book_id')
                ->orderBy('chapter_no')
                ->paginate($perPage, ['*'], 'page', $page);

            $formattedChapters = $chapters->map(function($chapter) use ($language) {
                return [
                    'id' => (string) $chapter->id,
                    'book_id' => (string) $chapter->book_id,
                    'chapter_no' => (string) $chapter->chapter_no,
                    'name' => $language === 'ar' && $chapter->name_ar ? $chapter->name_ar : $chapter->name_en,
                    'name_en' => $chapter->name_en,
                    'name_ar' => $chapter->name_ar,
                    'total_hadith' => (string) $chapter->total_hadith,
                    'book' => [
                        'id' => $chapter->book->id,
                        'code' => $chapter->book->code,
                        'name' => $language === 'ar' && $chapter->book->name_ar ? $chapter->book->name_ar : $chapter->book->name_en
                    ]
                ];
            });

            return $this->successResponse($formattedChapters, [
                'total' => $chapters->total(),
                'per_page' => $chapters->perPage(),
                'current_page' => $chapters->currentPage(),
                'last_page' => $chapters->lastPage()
            ]);

        } catch (\Exception $e) {
            Log::error('Chapters fetch error: ' . $e->getMessage());
            return $this->errorResponse('Failed to fetch chapters', $e->getMessage());
        }
    }

    /**
     * Get chapter details
     */
    public function getChapter($chapter): JsonResponse
    {
        try {
            $chapterModel = Chapter::with(['book:id,code,name_en,name_ar'])->find($chapter);
            
            if (!$chapterModel) {
                return $this->notFoundResponse('Chapter not found');
            }

            $language = request()->query('language', 'en');
            
            $chapterData = [
                'id' => (string) $chapterModel->id,
                'book_id' => (string) $chapterModel->book_id,
                'chapter_no' => (string) $chapterModel->chapter_no,
                'name' => $language === 'ar' && $chapterModel->name_ar ? $chapterModel->name_ar : $chapterModel->name_en,
                'name_en' => $chapterModel->name_en,
                'name_ar' => $chapterModel->name_ar,
                'total_hadith' => (string) $chapterModel->total_hadith,
                'book' => [
                    'id' => $chapterModel->book->id,
                    'code' => $chapterModel->book->code,
                    'name' => $language === 'ar' && $chapterModel->book->name_ar ? $chapterModel->book->name_ar : $chapterModel->book->name_en
                ]
            ];

            return $this->successResponse($chapterData);

        } catch (\Exception $e) {
            Log::error("Get chapter error: {$chapter}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch chapter', $e->getMessage());
        }
    }

    /**
     * Get hadiths for chapter by ID
     */
    public function chapterHadithsById($chapterId): JsonResponse
    {
        try {
            $chapter = Chapter::with(['book:id,code,name_en,name_ar'])->find($chapterId);
            
            if (!$chapter) {
                return $this->notFoundResponse('Chapter not found');
            }

            $request = request();
            $language = $request->query('language', 'en');
            $perPage = (int) $request->query('per_page', 20);
            $page = (int) $request->query('page', 1);

            $hadiths = Hadith::where('chapter_id', $chapterId)
                ->select('id', 'book_id', 'chapter_id', 'hadith_number', 'arabic_text', 'grade')
                ->orderBy('hadith_number')
                ->paginate($perPage, ['*'], 'page', $page);

            $formattedHadiths = $hadiths->map(function($hadith) use ($language) {
                return [
                    'id' => (string) $hadith->id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade
                ];
            });

            return $this->successResponse($formattedHadiths, [
                'chapter' => [
                    'id' => $chapter->id,
                    'chapter_no' => $chapter->chapter_no,
                    'name' => $language === 'ar' && $chapter->name_ar ? $chapter->name_ar : $chapter->name_en,
                    'book' => [
                        'id' => $chapter->book->id,
                        'code' => $chapter->book->code,
                        'name' => $language === 'ar' && $chapter->book->name_ar ? $chapter->book->name_ar : $chapter->book->name_en
                    ]
                ],
                'total' => $hadiths->total(),
                'per_page' => $hadiths->perPage(),
                'current_page' => $hadiths->currentPage(),
                'last_page' => $hadiths->lastPage()
            ]);

        } catch (\Exception $e) {
            Log::error("Chapter hadiths by ID error: {$chapterId}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch chapter hadiths', $e->getMessage());
        }
    }

    /**
     * Get hadith by ID
     */
    public function getHadithById($id): JsonResponse
    {
        try {
            $hadith = Hadith::with([
                'book:id,code,name_en,name_ar',
                'chapter:id,chapter_no,name_en,name_ar'
            ])->find($id);
            
            if (!$hadith) {
                return $this->notFoundResponse('Hadith not found');
            }

            $language = request()->query('language', 'en');
            $translation = HadithTranslation::where('hadith_id', $id)
                ->where('localization_code', $language)
                ->first();

            // Fallback to English if requested language not found
            if (!$translation && $language !== 'en') {
                $translation = HadithTranslation::where('hadith_id', $id)
                    ->where('localization_code', 'en')
                    ->first();
            }

            $hadithData = [
                'id' => (string) $hadith->id,
                'hadith_number' => $hadith->hadith_number,
                'arabic_text' => $hadith->arabic_text,
                'grade' => $hadith->grade,
                'references' => $hadith->references,
                'book' => [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                ],
                'chapter' => [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name' => $language === 'ar' && $hadith->chapter->name_ar ? $hadith->chapter->name_ar : $hadith->chapter->name_en
                ],
                'translation' => $translation ? [
                    'language' => $translation->localization_code,
                    'text' => $this->localizeNumbers($translation->translation_text, $language),
                    'explanation' => $this->localizeNumbers($translation->explanation, $language),
                    'hints' => $translation->hints
                ] : null
            ];

            return $this->successResponse($hadithData);

        } catch (\Exception $e) {
            Log::error("Get hadith by ID error: {$id}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch hadith', $e->getMessage());
        }
    }

    /**
     * Get hadith translation by ID
     */
    public function getHadithTranslationById($id, $lang): JsonResponse
    {
        try {
            $hadith = Hadith::with(['book:id,code,name_en,name_ar'])->find($id);
            
            if (!$hadith) {
                return $this->notFoundResponse('Hadith not found');
            }

            $translation = HadithTranslation::where('hadith_id', $id)
                ->where('localization_code', $lang)
                ->first();

            if (!$translation) {
                return $this->notFoundResponse("Translation not found for language '{$lang}'");
            }

            $translationData = [
                'hadith' => [
                    'id' => (string) $hadith->id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade,
                    'book' => [
                        'id' => $hadith->book->id,
                        'code' => $hadith->book->code,
                        'name' => $lang === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                    ]
                ],
                'translation' => [
                    'id' => $translation->id,
                    'language' => $translation->localization_code,
                    'text' => $this->localizeNumbers($translation->translation_text, $lang),
                    'explanation' => $this->localizeNumbers($translation->explanation, $lang),
                    'hints' => $translation->hints
                ]
            ];

            return $this->successResponse($translationData);

        } catch (\Exception $e) {
            Log::error("Get hadith translation error: {$id}/{$lang}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch translation', $e->getMessage());
        }
    }

    /**
     * Get hadith by book and number
     */
    public function getHadith($book, $hadith_number, $chapter = null): JsonResponse
    {
        try {
            $bookModel = $this->findBook($book);
            
            if (!$bookModel) {
                return $this->notFoundResponse('Book not found');
            }

            $query = Hadith::where('book_id', $bookModel->id)
                ->where('hadith_number', $hadith_number);

            if ($chapter) {
                $chapterModel = Chapter::where('book_id', $bookModel->id)
                    ->where('chapter_no', $chapter)
                    ->first();
                
                if ($chapterModel) {
                    $query->where('chapter_id', $chapterModel->id);
                }
            }

            $hadith = $query->with([
                'book:id,code,name_en,name_ar',
                'chapter:id,chapter_no,name_en,name_ar'
            ])->first();

            if (!$hadith) {
                return $this->notFoundResponse('Hadith not found');
            }

            $language = request()->query('language', 'en');

            $hadithData = [
                'id' => (string) $hadith->id,
                'hadith_number' => $hadith->hadith_number,
                'arabic_text' => $hadith->arabic_text,
                'grade' => $hadith->grade,
                'references' => $hadith->references,
                'book' => [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                ],
                'chapter' => [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name' => $language === 'ar' && $hadith->chapter->name_ar ? $hadith->chapter->name_ar : $hadith->chapter->name_en
                ]
            ];

            return $this->successResponse($hadithData);

        } catch (\Exception $e) {
            Log::error("Get hadith error: {$book}/{$hadith_number}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch hadith', $e->getMessage());
        }
    }

    /**
     * Get hadith translation
     */
    public function getHadithTranslation($book, $hadith_number, $lang, $chapter = null): JsonResponse
    {
        try {
            $bookModel = $this->findBook($book);
            
            if (!$bookModel) {
                return $this->notFoundResponse('Book not found');
            }

            $query = Hadith::where('book_id', $bookModel->id)
                ->where('hadith_number', $hadith_number);

            if ($chapter) {
                $chapterModel = Chapter::where('book_id', $bookModel->id)
                    ->where('chapter_no', $chapter)
                    ->first();
                
                if ($chapterModel) {
                    $query->where('chapter_id', $chapterModel->id);
                }
            }

            $hadith = $query->with(['book:id,code,name_en,name_ar'])->first();

            if (!$hadith) {
                return $this->notFoundResponse('Hadith not found');
            }

            $translation = HadithTranslation::where('hadith_id', $hadith->id)
                ->where('localization_code', $lang)
                ->first();

            if (!$translation) {
                return $this->notFoundResponse("Translation not found for language '{$lang}'");
            }

            $translationData = [
                'hadith' => [
                    'id' => (string) $hadith->id,
                    'book_id' => (string) $hadith->book_id,
                    'chapter_id' => (string) $hadith->chapter_id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade,
                    'book' => [
                        'id' => $hadith->book->id,
                        'code' => $hadith->book->code,
                        'name' => $lang === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                    ]
                ],
                'translation' => [
                    'language' => $translation->localization_code,
                    'text' => $this->localizeNumbers($translation->translation_text, $lang),
                    'explanation' => $this->localizeNumbers($translation->explanation, $lang),
                    'hints' => $translation->hints
                ]
            ];

            return $this->successResponse($translationData);

        } catch (\Exception $e) {
            Log::error("Get hadith translation error: {$book}/{$hadith_number}/{$lang}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch translation', $e->getMessage());
        }
    }

    /**
     * Search hadiths
     */
    public function search(Request $request): JsonResponse
    {
        try {
            $query = $request->get('q') ?: $request->get('query');
            $language = $request->get('language', 'en');
            $perPage = (int) $request->get('per_page', 20);
            $page = (int) $request->get('page', 1);

            if (!$query) {
                return $this->errorResponse('Search query is required (use ?q= or ?query=)', null, 400);
            }

            // Search in Arabic text
            $hadiths = Hadith::where('arabic_text', 'LIKE', "%{$query}%")
                ->select('id', 'book_id', 'chapter_id', 'hadith_number', 'arabic_text', 'grade')
                ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar'])
                ->orWhereHas('translations', function($q) use ($query, $language) {
                    $q->where('translation_text', 'LIKE', "%{$query}%")
                      ->where('localization_code', $language);
                })
                ->orderBy('id')
                ->paginate($perPage, ['*'], 'page', $page);

            $formattedHadiths = $hadiths->map(function($hadith) use ($language) {
                $translation = HadithTranslation::where('hadith_id', $hadith->id)
                    ->where('localization_code', $language)
                    ->first();

                return [
                    'id' => (string) $hadith->id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade,
                    'book' => [
                        'id' => $hadith->book->id,
                        'code' => $hadith->book->code,
                        'name' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                    ],
                    'chapter' => [
                        'id' => $hadith->chapter->id,
                        'chapter_no' => $hadith->chapter->chapter_no,
                        'name' => $language === 'ar' && $hadith->chapter->name_ar ? $hadith->chapter->name_ar : $hadith->chapter->name_en
                    ],
                    'translation' => $translation ? [
                        'language' => $translation->localization_code,
                        'text' => $this->localizeNumbers($translation->translation_text, $language)
                    ] : null
                ];
            });

            return $this->successResponse($formattedHadiths, [
                'query' => $query,
                'language' => $language,
                'total' => $hadiths->total(),
                'per_page' => $hadiths->perPage(),
                'current_page' => $hadiths->currentPage(),
                'last_page' => $hadiths->lastPage()
            ]);

        } catch (\Exception $e) {
            Log::error('Search error: ' . $e->getMessage());
            return $this->errorResponse('Search failed', $e->getMessage());
        }
    }

    /**
     * Search hadiths by term (path)
     */
    public function searchPath($term): JsonResponse
    {
        try {
            $hadiths = Hadith::where('arabic_text', 'LIKE', "%{$term}%")
                ->orWhereHas('translations', function($q) use ($term) {
                    $q->where('translation_text', 'LIKE', "%{$term}%");
                })
                ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar'])
                ->take(50)
                ->get();

            $formattedHadiths = $hadiths->map(function($hadith) {
                return [
                    'id' => (string) $hadith->id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade,
                    'book' => [
                        'id' => $hadith->book->id,
                        'code' => $hadith->book->code,
                        'name_en' => $hadith->book->name_en,
                        'name_ar' => $hadith->book->name_ar
                    ],
                    'chapter' => [
                        'id' => $hadith->chapter->id,
                        'chapter_no' => $hadith->chapter->chapter_no,
                        'name_en' => $hadith->chapter->name_en,
                        'name_ar' => $hadith->chapter->name_ar
                    ]
                ];
            });

            return $this->successResponse($formattedHadiths, [
                'query' => $term,
                'total' => $hadiths->count()
            ]);

        } catch (\Exception $e) {
            Log::error('Search path error: ' . $e->getMessage());
            return $this->errorResponse('Search failed', $e->getMessage());
        }
    }

    /**
     * Get random hadith
     */
    public function random(): JsonResponse
    {
        try {
            $language = request()->query('language', 'en');
            
            $hadith = Hadith::with([
                'book:id,code,name_en,name_ar',
                'chapter:id,chapter_no,name_en,name_ar'
            ])->inRandomOrder()->first();

            if (!$hadith) {
                return $this->notFoundResponse('No hadiths found');
            }

            $translation = HadithTranslation::where('hadith_id', $hadith->id)
                ->where('localization_code', $language)
                ->first();

            // Fallback to English if requested language not found
            if (!$translation && $language !== 'en') {
                $translation = HadithTranslation::where('hadith_id', $hadith->id)
                    ->where('localization_code', 'en')
                    ->first();
            }

            $hadithData = [
                'id' => (string) $hadith->id,
                'hadith_number' => $hadith->hadith_number,
                'arabic_text' => $hadith->arabic_text,
                'grade' => $hadith->grade,
                'book' => [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                ],
                'chapter' => [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name' => $language === 'ar' && $hadith->chapter->name_ar ? $hadith->chapter->name_ar : $hadith->chapter->name_en
                ],
                'translation' => $translation ? [
                    'language' => $translation->localization_code,
                    'text' => $this->localizeNumbers($translation->translation_text, $language)
                ] : null
            ];

            return $this->successResponse($hadithData);

        } catch (\Exception $e) {
            Log::error('Random hadith error: ' . $e->getMessage());
            return $this->errorResponse('Failed to get random hadith', $e->getMessage());
        }
    }

/**
 * Get all categories - FIXED VERSION (without category_localizations table)
 */
public function categories(Request $request): JsonResponse
{
    try {
        $language = $request->query('language', 'en');
        $perPage = (int) $request->query('per_page', 20);
        $page = (int) $request->query('page', 1);
        $parent = $request->query('parent');

        // Build query - use basic Category model without localizations
        $query = Category::query()
            ->select('id', 'parent_id', 'name_en', 'name_ar');

        if ($parent === 'null' || $parent === 'root') {
            $query->whereNull('parent_id');
        } elseif ($parent) {
            $query->where('parent_id', $parent);
        }

        // Count total
        $total = $query->count();

        // Get paginated results
        $categories = $query->orderBy('name_en')
            ->skip(($page - 1) * $perPage)
            ->take($perPage)
            ->get();

        $formattedCategories = $categories->map(function($category) use ($language) {
            // Get hadith count
            $hadithCount = DB::table('hadith_category')
                ->where('category_id', $category->id)
                ->count();

            // Determine which name to show based on language
            $title = $category->name_en; // Default to English
            if ($language === 'ar' && !empty($category->name_ar)) {
                $title = $category->name_ar; // Use Arabic if requested and available
            }

            return [
                'id' => (string) $category->id,
                'parent_id' => $category->parent_id ? (string) $category->parent_id : null,
                'title' => $title,
                'name_en' => $category->name_en,
                'name_ar' => $category->name_ar,
                'hadith_count' => (string) $hadithCount
            ];
        });

        $lastPage = ceil($total / $perPage);

        return $this->successResponse($formattedCategories, [
            'total' => $total,
            'per_page' => $perPage,
            'current_page' => $page,
            'last_page' => $lastPage,
            'filter' => ['parent' => $parent],
            'language' => $language
        ]);

    } catch (\Exception $e) {
        Log::error('Categories fetch error: ' . $e->getMessage());
        return $this->errorResponse('Failed to fetch categories', $e->getMessage());
    }
}

    /**
     * Get specific category
     */
    public function getCategory($category): JsonResponse
    {
        try {
            $categoryModel = Category::find($category);
            
            if (!$categoryModel) {
                return $this->notFoundResponse('Category not found');
            }

            $language = request()->query('language', 'en');
            $includeHadiths = request()->boolean('include_hadiths', false);
            $limit = (int) request()->query('limit', 10);

            // Get hadith count
            $hadithCount = DB::table('hadith_category')
                ->where('category_id', $categoryModel->id)
                ->count();

            $categoryData = [
                'id' => (string) $categoryModel->id,
                'parent_id' => $categoryModel->parent_id ? (string) $categoryModel->parent_id : null,
                'title' => $language === 'ar' && $categoryModel->name_ar ? $categoryModel->name_ar : $categoryModel->name_en,
                'name_en' => $categoryModel->name_en,
                'name_ar' => $categoryModel->name_ar,
                'hadith_count' => (string) $hadithCount,
                'subcategories' => Category::where('parent_id', $categoryModel->id)
                    ->get()
                    ->map(function($subcat) use ($language) {
                        $subHadithCount = DB::table('hadith_category')
                            ->where('category_id', $subcat->id)
                            ->count();

                        return [
                            'id' => (string) $subcat->id,
                            'title' => $language === 'ar' && $subcat->name_ar ? $subcat->name_ar : $subcat->name_en,
                            'hadith_count' => (string) $subHadithCount
                        ];
                    })
            ];

            if ($includeHadiths) {
                $hadiths = DB::table('hadith_category')
                    ->join('hadiths', 'hadith_category.hadith_id', '=', 'hadiths.id')
                    ->where('hadith_category.category_id', $categoryModel->id)
                    ->select('hadiths.id', 'hadiths.book_id', 'hadiths.chapter_id', 'hadiths.hadith_number', 'hadiths.arabic_text', 'hadiths.grade')
                    ->limit($limit)
                    ->get()
                    ->map(function($hadith) use ($language) {
                        $book = Book::find($hadith->book_id);
                        $chapter = Chapter::find($hadith->chapter_id);
                        $translation = HadithTranslation::where('hadith_id', $hadith->id)
                            ->where('localization_code', $language)
                            ->first();

                        // Fallback to English
                        if (!$translation && $language !== 'en') {
                            $translation = HadithTranslation::where('hadith_id', $hadith->id)
                                ->where('localization_code', 'en')
                                ->first();
                        }

                        return [
                            'id' => (string) $hadith->id,
                            'hadith_number' => $hadith->hadith_number,
                            'arabic_text' => $hadith->arabic_text,
                            'grade' => $hadith->grade,
                            'book' => $book ? [
                                'id' => $book->id,
                                'code' => $book->code,
                                'name' => $language === 'ar' && $book->name_ar ? $book->name_ar : $book->name_en
                            ] : null,
                            'chapter' => $chapter ? [
                                'id' => $chapter->id,
                                'chapter_no' => $chapter->chapter_no,
                                'name' => $language === 'ar' && $chapter->name_ar ? $chapter->name_ar : $chapter->name_en
                            ] : null,
                            'translation' => $translation ? [
                                'language' => $translation->localization_code,
                                'text' => $this->localizeNumbers($translation->translation_text, $language)
                            ] : null
                        ];
                    });

                $categoryData['hadiths'] = $hadiths;
            }

            return $this->successResponse($categoryData);

        } catch (\Exception $e) {
            Log::error("Get category error: {$category}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch category', $e->getMessage());
        }
    }

    /**
     * Get category children
     */
    public function categoryChildren($id, Request $request): JsonResponse
    {
        try {
            $parent = Category::find($id);
            
            if (!$parent) {
                return $this->notFoundResponse('Category not found');
            }

            $language = $request->query('language', 'en');

            $children = Category::where('parent_id', $id)
                ->get()
                ->map(function($category) use ($language) {
                    $hadithCount = DB::table('hadith_category')
                        ->where('category_id', $category->id)
                        ->count();

                    return [
                        'id' => (string) $category->id,
                        'parent_id' => (string) $category->parent_id,
                        'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en,
                        'hadith_count' => (string) $hadithCount
                    ];
                });

            return $this->successResponse($children, [
                'parent' => [
                    'id' => (string) $parent->id,
                    'title' => $language === 'ar' && $parent->name_ar ? $parent->name_ar : $parent->name_en
                ],
                'total' => $children->count()
            ]);

        } catch (\Exception $e) {
            Log::error("Category children error: {$id}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch category children', $e->getMessage());
        }
    }

    /**
     * Get category hadiths
     */
    public function categoryHadiths($categoryId): JsonResponse
    {
        try {
            $category = Category::find($categoryId);
            
            if (!$category) {
                return $this->notFoundResponse('Category not found');
            }

            $language = request()->query('language', 'en');
            $perPage = (int) request()->query('per_page', 20);
            $page = (int) request()->query('page', 1);

            // Count total
            $total = DB::table('hadith_category')
                ->where('category_id', $categoryId)
                ->count();

            $hadiths = DB::table('hadith_category')
                ->join('hadiths', 'hadith_category.hadith_id', '=', 'hadiths.id')
                ->where('hadith_category.category_id', $categoryId)
                ->select('hadiths.id', 'hadiths.book_id', 'hadiths.chapter_id', 'hadiths.hadith_number', 'hadiths.arabic_text', 'hadiths.grade')
                ->skip(($page - 1) * $perPage)
                ->take($perPage)
                ->get()
                ->map(function($hadith) use ($language) {
                    $book = Book::find($hadith->book_id);
                    $chapter = Chapter::find($hadith->chapter_id);
                    $translation = HadithTranslation::where('hadith_id', $hadith->id)
                        ->where('localization_code', $language)
                        ->first();

                    return [
                        'id' => (string) $hadith->id,
                        'hadith_number' => $hadith->hadith_number,
                        'arabic_text' => $hadith->arabic_text,
                        'grade' => $hadith->grade,
                        'book' => $book ? [
                            'id' => $book->id,
                            'code' => $book->code,
                            'name' => $language === 'ar' && $book->name_ar ? $book->name_ar : $book->name_en
                        ] : null,
                        'chapter' => $chapter ? [
                            'id' => $chapter->id,
                            'chapter_no' => $chapter->chapter_no,
                            'name' => $language === 'ar' && $chapter->name_ar ? $chapter->name_ar : $chapter->name_en
                        ] : null,
                        'translation' => $translation ? [
                            'language' => $translation->localization_code,
                            'text' => $this->localizeNumbers($translation->translation_text, $language)
                        ] : null
                    ];
                });

            $lastPage = ceil($total / $perPage);

            return $this->successResponse($hadiths, [
                'category' => [
                    'id' => (string) $category->id,
                    'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en
                ],
                'total' => $total,
                'per_page' => $perPage,
                'current_page' => $page,
                'last_page' => $lastPage
            ]);

        } catch (\Exception $e) {
            Log::error("Category hadiths error: {$categoryId}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch category hadiths', $e->getMessage());
        }
    }

    /**
     * Get root categories
     */
    public function rootCategories(Request $request): JsonResponse
    {
        try {
            $language = $request->query('language', 'en');

            $categories = Category::whereNull('parent_id')
                ->get()
                ->map(function($category) use ($language) {
                    $hadithCount = DB::table('hadith_category')
                        ->where('category_id', $category->id)
                        ->count();

                    return [
                        'id' => (string) $category->id,
                        'parent_id' => null,
                        'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en,
                        'hadith_count' => (string) $hadithCount
                    ];
                });

            return $this->successResponse($categories, [
                'total' => $categories->count()
            ]);

        } catch (\Exception $e) {
            Log::error('Root categories error: ' . $e->getMessage());
            return $this->errorResponse('Failed to fetch root categories', $e->getMessage());
        }
    }

    /**
     * HadeethEnc compatible: List hadiths
     */
    public function hadeethsList(Request $request): JsonResponse
    {
        try {
            $language = $request->query('language', 'en');
            $categoryId = $request->query('category_id');
            $page = (int) $request->query('page', 1);
            $perPage = (int) $request->query('per_page', 20);

            if (!$categoryId) {
                return $this->errorResponse('category_id is required', null, 400);
            }

            $category = Category::find($categoryId);
            if (!$category) {
                return $this->notFoundResponse('Category not found');
            }

            // Get hadiths from pivot table
            $total = DB::table('hadith_category')
                ->where('category_id', $categoryId)
                ->count();

            $hadithIds = DB::table('hadith_category')
                ->where('category_id', $categoryId)
                ->skip(($page - 1) * $perPage)
                ->take($perPage)
                ->pluck('hadith_id');

            $hadiths = Hadith::whereIn('id', $hadithIds)
                ->with(['translations'])
                ->get();

            $data = $hadiths->map(function($hadith) use ($language) {
                $title = $hadith->arabic_text ?? '';
                
                if ($language !== 'ar') {
                    $translation = $hadith->translations->where('localization_code', $language)->first();
                    if ($translation && $translation->translation_text) {
                        $title = $translation->translation_text;
                    }
                }

                $translations = $hadith->translations->pluck('localization_code')->unique()->values()->all();
                if (!in_array('ar', $translations)) {
                    array_unshift($translations, 'ar');
                }

                $truncatedTitle = mb_strlen($title) > 200 ? mb_substr($title, 0, 200) . '...' : $title;

                return [
                    'id' => (string) $hadith->id,
                    'title' => $truncatedTitle,
                    'translations' => $translations
                ];
            });

            $lastPage = ceil($total / $perPage);

            return $this->successResponse($data, [
                'current_page' => (string) $page,
                'last_page' => $lastPage,
                'total_items' => $total,
                'per_page' => (string) $perPage,
                'category' => [
                    'id' => (string) $category->id,
                    'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en
                ]
            ]);

        } catch (\Exception $e) {
            Log::error('Hadeeths list error: ' . $e->getMessage());
            return $this->errorResponse('Failed to fetch hadeeths list', $e->getMessage());
        }
    }

    /**
     * HadeethEnc compatible: Get single hadith
     */
    public function hadeethOne(Request $request): JsonResponse
    {
        try {
            $hadeethId = $request->query('id');
            $language = $request->query('language', 'en');

            if (!$hadeethId) {
                return $this->errorResponse('id parameter is required', null, 400);
            }

            $hadith = Hadith::with(['book', 'chapter', 'translations'])->find($hadeethId);
            
            if (!$hadith) {
                return $this->notFoundResponse('Hadith not found');
            }

            // Get category IDs
            $categoryIds = DB::table('hadith_category')
                ->where('hadith_id', $hadeethId)
                ->pluck('category_id')
                ->map(fn($id) => (string) $id)
                ->toArray();

            // Get translation languages
            $translations = HadithTranslation::where('hadith_id', $hadeethId)
                ->pluck('localization_code')
                ->unique()
                ->toArray();
            if (!in_array('ar', $translations)) {
                array_unshift($translations, 'ar');
            }

            // Format response similar to HadeethEnc API
            $response = [
                'id' => (string) $hadith->id,
                'title' => '',
                'hadeeth' => '',
                'attribution' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en,
                'grade' => $hadith->grade ?: 'Not graded',
                'explanation' => '',
                'hints' => [],
                'categories' => $categoryIds,
                'translations' => $translations,
                'references' => [],
                'references_numbered' => []
            ];

            // Add Arabic fields
            $response['hadeeth_ar'] = $hadith->arabic_text ?: '';
            $response['explanation_ar'] = $hadith->explanation ?? '';
            $response['attribution_ar'] = $hadith->book->name_ar ?? '';
            $response['grade_ar'] = $hadith->grade ?? '';

            if ($language === 'ar') {
                // Arabic response
                $arabicText = $hadith->arabic_text ?: '';
                $response['title'] = mb_strlen($arabicText) > 100 ? mb_substr($arabicText, 0, 100) : $arabicText;
                $response['hadeeth'] = $arabicText;
                $response['explanation'] = $hadith->explanation ?? '';
                
                // Parse references if they exist
                if ($hadith->references) {
                    $references = is_string($hadith->references) ? json_decode($hadith->references, true) : $hadith->references;
                    if (is_array($references)) {
                        $response['references'] = array_values(array_filter($references));
                        foreach ($response['references'] as $i => $ref) {
                            $response['references_numbered'][$i + 1] = $ref;
                        }
                    }
                }
            } else {
                // Non-Arabic response
                $translation = $hadith->translations->where('localization_code', $language)->first();
                
                if (!$translation && $language !== 'en') {
                    $translation = $hadith->translations->where('localization_code', 'en')->first();
                }

                if ($translation) {
                    $translationText = $translation->translation_text ?? '';
                    $response['title'] = mb_strlen($translationText) > 100 ? mb_substr($translationText, 0, 100) : $translationText;
                    $response['hadeeth'] = $translationText;
                    $response['explanation'] = $translation->explanation ?? '';
                    $response['hints'] = $translation->hints ?? [];
                } else {
                    // Fallback to Arabic
                    $arabicText = $hadith->arabic_text ?: '';
                    $response['title'] = mb_strlen($arabicText) > 100 ? mb_substr($arabicText, 0, 100) : $arabicText;
                    $response['hadeeth'] = $arabicText;
                }
            }

            // Remove empty fields
            $response = array_filter($response, function($value) {
                return !empty($value) || $value === 0 || $value === '0';
            });

            return $this->successResponse(['hadith' => $response]);

        } catch (\Exception $e) {
            Log::error("Hadeeth one error: {$hadeethId}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch hadeeth', $e->getMessage());
        }
    }

    /**
     * Get hadiths by topic
     */
    public function topicHadiths($topic): JsonResponse
    {
        try {
            $language = request()->query('language', 'en');
            $perPage = (int) request()->query('per_page', 20);
            $page = (int) request()->query('page', 1);

            $chapters = Chapter::where('name_en', 'LIKE', "%{$topic}%")
                ->orWhere('name_ar', 'LIKE', "%{$topic}%")
                ->pluck('id');

            $hadiths = Hadith::whereIn('chapter_id', $chapters)
                ->select('id', 'book_id', 'chapter_id', 'hadith_number', 'arabic_text', 'grade')
                ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar'])
                ->paginate($perPage, ['*'], 'page', $page);

            $formattedHadiths = $hadiths->map(function($hadith) use ($language) {
                return [
                    'id' => (string) $hadith->id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade,
                    'book' => [
                        'id' => $hadith->book->id,
                        'code' => $hadith->book->code,
                        'name' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                    ],
                    'chapter' => [
                        'id' => $hadith->chapter->id,
                        'chapter_no' => $hadith->chapter->chapter_no,
                        'name' => $language === 'ar' && $hadith->chapter->name_ar ? $hadith->chapter->name_ar : $hadith->chapter->name_en
                    ]
                ];
            });

            return $this->successResponse($formattedHadiths, [
                'topic' => $topic,
                'chapters_found' => $chapters->count(),
                'total' => $hadiths->total(),
                'per_page' => $hadiths->perPage(),
                'current_page' => $hadiths->currentPage(),
                'last_page' => $hadiths->lastPage()
            ]);

        } catch (\Exception $e) {
            Log::error("Topic hadiths error: {$topic}", ['error' => $e->getMessage()]);
            return $this->errorResponse('Failed to fetch topic hadiths', $e->getMessage());
        }
    }

    /**
     * Get supported languages
     */
    public function languages(): JsonResponse
    {
        $languages = [
            ['code' => 'ar', 'native' => 'عربي'],
            ['code' => 'en', 'native' => 'English'],
            ['code' => 'fr', 'native' => 'Français'],
            ['code' => 'es', 'native' => 'Español'],
            ['code' => 'tr', 'native' => 'Türkçe'],
            ['code' => 'ur', 'native' => 'اردو'],
            ['code' => 'id', 'native' => 'Indonesia'],
            ['code' => 'bs', 'native' => 'Bosanski'],
            ['code' => 'ru', 'native' => 'Русский'],
            ['code' => 'bn', 'native' => 'বাংলা ভাষা'],
            ['code' => 'zh', 'native' => '中文'],
            ['code' => 'fa', 'native' => 'فارسی'],
            ['code' => 'tl', 'native' => 'Tagalog'],
            ['code' => 'hi', 'native' => 'हिन्दी'],
            ['code' => 'vi', 'native' => 'Tiếng Việt'],
            ['code' => 'si', 'native' => 'සිංහල'],
            ['code' => 'ug', 'native' => 'ئۇيغۇرچە'],
        ];

        return $this->successResponse($languages);
    }

    /**
     * Admin: Sync missing translations (simplified)
     */
    public function syncMissingTranslations(Request $request): JsonResponse
    {
        try {
            // This endpoint should be protected by middleware
            $lang = $request->get('lang', 'bn');
            $books = $request->get('books');
            $limit = (int) $request->get('limit', 0);
            $dryRun = filter_var($request->get('dry_run', true), FILTER_VALIDATE_BOOLEAN);
            
            // Simple response for now
            return $this->successResponse([
                'message' => 'Sync initiated (placeholder)',
                'parameters' => [
                    'lang' => $lang,
                    'books' => $books,
                    'limit' => $limit,
                    'dry_run' => $dryRun
                ],
                'note' => 'Actual sync implementation would run in background'
            ]);

        } catch (\Exception $e) {
            Log::error('Sync missing translations error: ' . $e->getMessage());
            return $this->errorResponse('Failed to initiate sync', $e->getMessage());
        }
    }

    /**
     * Simple Welcome Page for Web Interface
     */
    public function simpleWelcome()
    {
        try {
            $stats = [
                'books' => Book::count(),
                'chapters' => Chapter::count(),
                'hadiths' => Hadith::count(),
            ];

            return view('hadith.welcome', ['stats' => $stats]);

        } catch (\Exception $e) {
            // If database is not ready, show basic welcome
            return view('hadith.welcome', ['stats' => null]);
        }
    }

    /**
     * Simple Books List for Web Interface
     */
    public function simpleBooks()
    {
        try {
            $books = Book::select('id', 'code', 'name_en', 'name_ar', 'total_hadith')
                        ->get()
                        ->take(10); // Limit for testing

            return view('hadith.books-simple', [
                'books' => $books,
                'totalBooks' => Book::count()
            ]);

        } catch (\Exception $e) {
            return response()->json([
                'error' => 'Database not ready. Please run migrations first.',
                'message' => $e->getMessage()
            ], 500);
        }
    }

    /**
     * Simple Book Show for Web Interface
     */
    public function simpleBookShow($id)
    {
        try {
            $book = Book::with(['chapters' => function($query) {
                $query->select('id', 'book_id', 'chapter_no', 'name_en', 'total_hadith')
                      ->orderBy('chapter_no');
            }])->findOrFail($id);

            return view('hadith.book-simple', [
                'book' => $book,
                'chapters' => $book->chapters
            ]);

        } catch (\Exception $e) {
            return response()->json([
                'error' => 'Book not found',
                'message' => $e->getMessage()
            ], 404);
        }
    }
}