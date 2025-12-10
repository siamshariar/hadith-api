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

        return str_replace(range(0, 9), $numeralMaps[$languageCode], $text);
    }

    /**
     * API Information
     */
    public function info(): JsonResponse
    {
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
            'version' => '1.1.0',
            'description' => 'Comprehensive Hadith database with multiple translations and API compatibility',
            'statistics' => $stats,
            'endpoints' => $endpoints,
            'defaults' => [
                'language' => 'en',
                'per_page' => 20,
                'page' => 1
            ]
        ]);
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
        $language = $request->query('language', 'en');
        $perPage = (int) $request->query('per_page', 20);
        $page = (int) $request->query('page', 1);

        $books = Book::withCount('chapters')
            ->orderBy('id')
            ->paginate($perPage, ['*'], 'page', $page);

        $formattedBooks = $books->map(function($book) use ($language) {
            return [
                'id' => (string) $book->id,
                'code' => $book->code,
                'name' => $language === 'ar' && $book->name_ar ? $book->name_ar : $book->name_en,
                'name_en' => $book->name_en,
                'name_ar' => $book->name_ar,
                'total_hadith' => (string) $book->total_hadith,
                'total_chapters' => (string) $book->chapters_count
            ];
        });

        return $this->successResponse($formattedBooks, [
            'total' => $books->total(),
            'per_page' => $books->perPage(),
            'current_page' => $books->currentPage(),
            'last_page' => $books->lastPage()
        ]);
    }

    /**
     * Get specific book
     */
    public function getBook($book): JsonResponse
    {
        $bookModel = $this->findBook($book);

        if (!$bookModel) {
            return $this->notFoundResponse('Book not found');
        }

        $language = request()->query('language', 'en');

        $chapters = $bookModel->chapters()
            ->select('id', 'chapter_no', 'name_en', 'name_ar', 'total_hadith')
            ->orderBy('chapter_no')
            ->get();

        $bookData = [
            'id' => (string) $bookModel->id,
            'code' => $bookModel->code,
            'name' => $language === 'ar' && $bookModel->name_ar ? $bookModel->name_ar : $bookModel->name_en,
            'name_en' => $bookModel->name_en,
            'name_ar' => $bookModel->name_ar,
            'total_hadith' => (string) $bookModel->total_hadith,
            'total_chapters' => (string) $chapters->count(),
            'chapters' => $chapters->map(function($chapter) use ($language) {
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
    }

    /**
     * Get book chapters
     */
    public function bookChapters($book): JsonResponse
    {
        $bookModel = $this->findBook($book);

        if (!$bookModel) {
            return $this->notFoundResponse('Book not found');
        }

        $language = request()->query('language', 'en');
        $perPage = (int) request()->query('per_page', 50);
        $page = (int) request()->query('page', 1);

        $chapters = Chapter::where('book_id', $bookModel->id)
            ->select('id', 'chapter_no', 'name_en', 'name_ar', 'total_hadith')
            ->orderBy('chapter_no')
            ->paginate($perPage, ['*'], 'page', $page);

        $formattedChapters = $chapters->map(function($chapter) use ($language) {
            return [
                'id' => (string) $chapter->id,
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
    }

    /**
     * Get chapter hadiths
     */
    public function chapterHadiths(Request $request, $book, $chapter): JsonResponse
    {
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
            ->select('id', 'hadith_number', 'arabic_text', 'grade', 'references')
            ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar', 'translations'])
            ->orderBy('hadith_number')
            ->paginate($perPage, ['*'], 'page', $page);

        $formattedHadiths = $hadiths->map(function($hadith) {
            return [
                'id' => (string) $hadith->id,
                'hadith_number' => $hadith->hadith_number,
                'arabic_text' => $hadith->arabic_text,
                'grade' => $hadith->grade,
                'references' => $hadith->references ? (is_string($hadith->references) ? json_decode($hadith->references, true) : $hadith->references) : [],
                'book' => $hadith->book ? [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name' => $hadith->book->name_en
                ] : null,
                'chapter' => $hadith->chapter ? [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name' => $hadith->chapter->name_en
                ] : null,
                'translations' => $hadith->translations->map(function($translation) {
                    return [
                        'language' => $translation->localization_code,
                        'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                        'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                        'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                    ];
                })
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
        $language = $request->query('language', 'en');
        $perPage = (int) $request->query('per_page', 20);
        $page = (int) $request->query('page', 1);

        $hadiths = Hadith::select('id', 'book_id', 'chapter_id', 'hadith_number', 'arabic_text', 'grade')
            ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar'])
            ->orderBy('id')
            ->paginate($perPage, ['*'], 'page', $page);

        $formattedHadiths = $hadiths->map(function($hadith) use ($language) {
            return [
                'id' => (string) $hadith->id,
                'hadith_number' => $hadith->hadith_number,
                'arabic_text' => $hadith->arabic_text,
                'grade' => $hadith->grade,
                'book' => $hadith->book ? [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en
                ] : null,
                'chapter' => $hadith->chapter ? [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name' => $language === 'ar' && $hadith->chapter->name_ar ? $hadith->chapter->name_ar : $hadith->chapter->name_en
                ] : null
            ];
        });

        return $this->successResponse($formattedHadiths, [
            'total' => $hadiths->total(),
            'per_page' => $hadiths->perPage(),
            'current_page' => $hadiths->currentPage(),
            'last_page' => $hadiths->lastPage()
        ]);
    }

    /**
     * Get all chapters
     */
    public function chapters(Request $request): JsonResponse
    {
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
                'book' => $chapter->book ? [
                    'id' => $chapter->book->id,
                    'code' => $chapter->book->code,
                    'name' => $language === 'ar' && $chapter->book->name_ar ? $chapter->book->name_ar : $chapter->book->name_en
                ] : null
            ];
        });

        return $this->successResponse($formattedChapters, [
            'total' => $chapters->total(),
            'per_page' => $chapters->perPage(),
            'current_page' => $chapters->currentPage(),
            'last_page' => $chapters->lastPage()
        ]);
    }

    /**
     * Get chapter details
     */
    public function getChapter($chapter): JsonResponse
    {
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
            'book' => $chapterModel->book ? [
                'id' => $chapterModel->book->id,
                'code' => $chapterModel->book->code,
                'name' => $language === 'ar' && $chapterModel->book->name_ar ? $chapterModel->book->name_ar : $chapterModel->book->name_en
            ] : null
        ];

        return $this->successResponse($chapterData);
    }

    /**
     * Get hadiths for chapter by ID
     */
    public function chapterHadithsById($chapterId): JsonResponse
    {
        $chapter = Chapter::with(['book:id,code,name_en,name_ar'])->find($chapterId);

        if (!$chapter) {
            return $this->notFoundResponse('Chapter not found');
        }

        $request = request();
        $language = $request->query('language', 'en');
        $perPage = (int) $request->query('per_page', 20);
        $page = (int) $request->query('page', 1);

        $hadiths = Hadith::where('chapter_id', $chapterId)
            ->select('id', 'hadith_number', 'arabic_text', 'grade')
            ->orderBy('hadith_number')
            ->paginate($perPage, ['*'], 'page', $page);

        $formattedHadiths = $hadiths->map(function($hadith) {
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
                'book' => $chapter->book ? [
                    'id' => $chapter->book->id,
                    'code' => $chapter->book->code,
                    'name' => $language === 'ar' && $chapter->book->name_ar ? $chapter->book->name_ar : $chapter->book->name_en
                ] : null
            ],
            'total' => $hadiths->total(),
            'per_page' => $hadiths->perPage(),
            'current_page' => $hadiths->currentPage(),
            'last_page' => $hadiths->lastPage()
        ]);
    }

    /**
     * Get hadith by ID
     */
    public function getHadithById($id): JsonResponse
    {
        $hadith = Hadith::with([
            'book:id,code,name_en,name_ar',
            'chapter:id,chapter_no,name_en,name_ar',
            'translations'
        ])->find($id);

        if (!$hadith) {
            return $this->notFoundResponse('Hadith not found');
        }

        $hadithData = [
            'id' => (string) $hadith->id,
            'hadith_number' => $hadith->hadith_number,
            'arabic_text' => $hadith->arabic_text,
            'grade' => $hadith->grade,
            'references' => $hadith->references ? (is_string($hadith->references) ? json_decode($hadith->references, true) : $hadith->references) : [],
            'book' => $hadith->book ? [
                'id' => $hadith->book->id,
                'code' => $hadith->book->code,
                'name' => $hadith->book->name_en
            ] : null,
            'chapter' => $hadith->chapter ? [
                'id' => $hadith->chapter->id,
                'chapter_no' => $hadith->chapter->chapter_no,
                'name' => $hadith->chapter->name_en
            ] : null,
            'translations' => $hadith->translations->map(function($translation) {
                return [
                    'language' => $translation->localization_code,
                    'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                    'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                    'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                ];
            })
        ];

        return $this->successResponse($hadithData);
    }

    /**
     * Get hadith translation by ID
     */
    public function getHadithTranslationById($id, $lang): JsonResponse
    {
        return redirect()->route('getHadithById', ['id' => $id], 301);
    }

    /**
     * Get hadith by book and number
     */
    public function getHadith($book, $hadith_number): JsonResponse
    {
        $bookModel = $this->findBook($book);

        if (!$bookModel) {
            return $this->notFoundResponse('Book not found');
        }

        $hadith = Hadith::where('book_id', $bookModel->id)
            ->where('hadith_number', $hadith_number)
            ->with([
                'book:id,code,name_en,name_ar',
                'chapter:id,chapter_no,name_en,name_ar',
                'translations'
            ])->first();

        if (!$hadith) {
            return $this->notFoundResponse('Hadith not found');
        }

        $hadithData = [
            'id' => (string) $hadith->id,
            'hadith_number' => $hadith->hadith_number,
            'arabic_text' => $hadith->arabic_text,
            'grade' => $hadith->grade,
            'references' => $hadith->references ? (is_string($hadith->references) ? json_decode($hadith->references, true) : $hadith->references) : [],
            'book' => $hadith->book ? [
                'id' => $hadith->book->id,
                'code' => $hadith->book->code,
                'name' => $hadith->book->name_en
            ] : null,
            'chapter' => $hadith->chapter ? [
                'id' => $hadith->chapter->id,
                'chapter_no' => $hadith->chapter->chapter_no,
                'name' => $hadith->chapter->name_en
            ] : null,
            'translations' => $hadith->translations->map(function($translation) {
                return [
                    'language' => $translation->localization_code,
                    'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                    'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                    'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                ];
            })
        ];

        return $this->successResponse($hadithData);
    }

    /**
     * Get hadith by book, chapter, and number
     */
    public function getHadithByBookChapterAndNumber($book, $chapter, $hadith_number): JsonResponse
    {
        $bookModel = $this->findBook($book);

        if (!$bookModel) {
            return $this->notFoundResponse('Book not found');
        }

        $chapterModel = $this->findChapter($bookModel->id, $chapter);
        if (!$chapterModel) {
            return $this->notFoundResponse('Chapter not found');
        }

        $hadith = Hadith::where('book_id', $bookModel->id)
            ->where('chapter_id', $chapterModel->id)
            ->where('hadith_number', $hadith_number)
            ->with([
                'book:id,code,name_en,name_ar',
                'chapter:id,chapter_no,name_en,name_ar',
                'translations'
            ])->first();

        if (!$hadith) {
            return $this->notFoundResponse('Hadith not found');
        }

        $hadithData = [
            'id' => (string) $hadith->id,
            'hadith_number' => $hadith->hadith_number,
            'arabic_text' => $hadith->arabic_text,
            'grade' => $hadith->grade,
            'references' => $hadith->references ? (is_string($hadith->references) ? json_decode($hadith->references, true) : $hadith->references) : [],
            'book' => $hadith->book ? [
                'id' => $hadith->book->id,
                'code' => $hadith->book->code,
                'name' => $hadith->book->name_en
            ] : null,
            'chapter' => $hadith->chapter ? [
                'id' => $hadith->chapter->id,
                'chapter_no' => $hadith->chapter->chapter_no,
                'name' => $hadith->chapter->name_en
            ] : null,
            'translations' => $hadith->translations->map(function($translation) {
                return [
                    'language' => $translation->localization_code,
                    'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                    'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                    'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                ];
            })
        ];

        return $this->successResponse($hadithData);
    }

    /**
     * Get hadith translation
     */
    public function getHadithTranslation($book, $hadith_number, $lang): JsonResponse
    {
        return redirect()->route('getHadith', ['book' => $book, 'hadith_number' => $hadith_number], 301);
    }

    /**
     * Get hadith translation by book, chapter, and number
     */
    public function getHadithTranslationByBookChapterAndNumber($book, $chapter, $hadith_number, $lang): JsonResponse
    {
        return redirect()->route('getHadithByBookChapterAndNumber', ['book' => $book, 'chapter' => $chapter, 'hadith_number' => $hadith_number], 301);
    }

    /**
     * Search hadiths
     */
    public function search(Request $request): JsonResponse
    {
        $query = $request->get('q') ?: $request->get('query');
        $language = $request->get('language', 'en');
        $perPage = (int) $request->get('per_page', 20);
        $page = (int) $request->get('page', 1);

        if (!$query) {
            return $this->errorResponse('Search query is required (use ?q= or ?query=)', null, 400);
        }

        $hadiths = Hadith::where('arabic_text', 'LIKE', "%{$query}%")
            ->orWhereHas('translations', function($q) use ($query, $language) {
                $q->where('translation_text', 'LIKE', "%{$query}%")
                    ->where('localization_code', $language);
            })
            ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar', 'translations'])
            ->paginate($perPage, ['*'], 'page', $page);

        $formattedHadiths = $hadiths->map(function($hadith) {
            return [
                'id' => (string) $hadith->id,
                'hadith_number' => $hadith->hadith_number,
                'arabic_text' => $hadith->arabic_text,
                'grade' => $hadith->grade,
                'book' => $hadith->book ? [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name' => $hadith->book->name_en
                ] : null,
                'chapter' => $hadith->chapter ? [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name' => $hadith->chapter->name_en
                ] : null,
                'translations' => $hadith->translations->map(function($translation) {
                    return [
                        'language' => $translation->localization_code,
                        'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                        'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                        'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                    ];
                })
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
    }

    /**
     * Search hadiths by term (path)
     */
    public function searchPath($term): JsonResponse
    {
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
                'book' => $hadith->book ? [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name_en' => $hadith->book->name_en,
                    'name_ar' => $hadith->book->name_ar
                ] : null,
                'chapter' => $hadith->chapter ? [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name_en' => $hadith->chapter->name_en,
                    'name_ar' => $hadith->chapter->name_ar
                ] : null
            ];
        });

        return $this->successResponse($formattedHadiths, [
            'query' => $term,
            'total' => $hadiths->count()
        ]);
    }

    /**
     * Get random hadith
     */
    public function random(): JsonResponse
    {
        $hadith = Hadith::with([
            'book:id,code,name_en,name_ar',
            'chapter:id,chapter_no,name_en,name_ar',
            'translations'
        ])->inRandomOrder()->first();

        if (!$hadith) {
            return $this->notFoundResponse('No hadiths found');
        }

        $hadithData = [
            'id' => (string) $hadith->id,
            'hadith_number' => $hadith->hadith_number,
            'arabic_text' => $hadith->arabic_text,
            'grade' => $hadith->grade,
            'book' => $hadith->book ? [
                'id' => $hadith->book->id,
                'code' => $hadith->book->code,
                'name' => $hadith->book->name_en
            ] : null,
            'chapter' => $hadith->chapter ? [
                'id' => $hadith->chapter->id,
                'chapter_no' => $hadith->chapter->chapter_no,
                'name' => $hadith->chapter->name_en
            ] : null,
            'translations' => $hadith->translations->map(function($translation) {
                return [
                    'language' => $translation->localization_code,
                    'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                    'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                    'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                ];
            })
        ];

        return $this->successResponse($hadithData);
    }

    /**
     * Get all categories - FIXED VERSION (without deleted_at)
     */
    public function categories(Request $request): JsonResponse
    {
        $language = $request->query('language', 'en');
        $perPage = (int) $request->query('per_page', 20);
        $page = (int) $request->query('page', 1);
        $parent = $request->query('parent');

        $query = Category::withCount('hadiths')
            ->select('id', 'parent_id', 'name_en', 'name_ar');

        if ($parent === 'null' || $parent === 'root') {
            $query->whereNull('parent_id');
        } elseif ($parent) {
            $query->where('parent_id', $parent);
        }

        $categories = $query->orderBy('name_en')->paginate($perPage, ['*'], 'page', $page);

        $formattedCategories = $categories->map(function($category) use ($language) {
            return [
                'id' => (string) $category->id,
                'parent_id' => $category->parent_id ? (string) $category->parent_id : null,
                'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en,
                'name_en' => $category->name_en,
                'name_ar' => $category->name_ar,
                'hadith_count' => (string) $category->hadiths_count
            ];
        });

        return $this->successResponse($formattedCategories, [
            'total' => $categories->total(),
            'per_page' => $categories->perPage(),
            'current_page' => $categories->currentPage(),
            'last_page' => $categories->lastPage(),
            'filter' => ['parent' => $parent]
        ]);
    }

    /**
     * Get specific category
     */
    public function getCategory($category): JsonResponse
    {
        $categoryModel = Category::withCount('hadiths', 'children')->find($category);

        if (!$categoryModel) {
            return $this->notFoundResponse('Category not found');
        }

        $language = request()->query('language', 'en');
        $includeHadiths = request()->boolean('include_hadiths', false);
        $limit = (int) request()->query('limit', 10);

        $categoryData = [
            'id' => (string) $categoryModel->id,
            'parent_id' => $categoryModel->parent_id ? (string) $categoryModel->parent_id : null,
            'title' => $language === 'ar' && $categoryModel->name_ar ? $categoryModel->name_ar : $categoryModel->name_en,
            'name_en' => $categoryModel->name_en,
            'name_ar' => $categoryModel->name_ar,
            'hadith_count' => (string) $categoryModel->hadiths_count,
            'subcategories_count' => (string) $categoryModel->children_count,
        ];

        if ($includeHadiths) {
            $hadiths = $categoryModel->hadiths()
                ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar', 'translations'])
                ->limit($limit)
                ->get();

            $categoryData['hadiths'] = $hadiths->map(function($hadith) {
                return [
                    'id' => (string) $hadith->id,
                    'hadith_number' => $hadith->hadith_number,
                    'arabic_text' => $hadith->arabic_text,
                    'grade' => $hadith->grade,
                    'book' => $hadith->book ? [
                        'id' => $hadith->book->id,
                        'code' => $hadith->book->code,
                        'name' => $hadith->book->name_en,
                    ] : null,
                    'chapter' => $hadith->chapter ? [
                        'id' => $hadith->chapter->id,
                        'chapter_no' => $hadith->chapter->chapter_no,
                        'name' => $hadith->chapter->name_en,
                    ] : null,
                    'translations' => $hadith->translations->map(function($translation) {
                        return [
                            'language' => $translation->localization_code,
                            'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                            'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                            'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                        ];
                    })
                ];
            });
        }

        return $this->successResponse($categoryData);
    }

    /**
     * Get category children
     */
    public function categoryChildren($id, Request $request): JsonResponse
    {
        $parent = Category::find($id);

        if (!$parent) {
            return $this->notFoundResponse('Category not found');
        }

        $language = $request->query('language', 'en');

        $children = Category::where('parent_id', $id)
            ->withCount('hadiths')
            ->get()
            ->map(function($category) use ($language) {
                return [
                    'id' => (string) $category->id,
                    'parent_id' => (string) $category->parent_id,
                    'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en,
                    'hadith_count' => (string) $category->hadiths_count
                ];
            });

        return $this->successResponse($children, [
            'parent' => [
                'id' => (string) $parent->id,
                'title' => $language === 'ar' && $parent->name_ar ? $parent->name_ar : $parent->name_en
            ],
            'total' => $children->count()
        ]);
    }

    /**
     * Get category hadiths
     */
    public function categoryHadiths($categoryId): JsonResponse
    {
        $category = Category::find($categoryId);

        if (!$category) {
            return $this->notFoundResponse('Category not found');
        }

        $language = request()->query('language', 'en');
        $perPage = (int) request()->query('per_page', 20);
        $page = (int) request()->query('page', 1);

        $hadiths = Hadith::whereHas('categories', fn($q) => $q->where('category_id', $categoryId))
            ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar', 'translations'])
            ->paginate($perPage, ['*'], 'page', $page);

        $formattedHadiths = $hadiths->map(function($hadith) {
            return [
                'id' => (string) $hadith->id,
                'hadith_number' => $hadith->hadith_number,
                'arabic_text' => $hadith->arabic_text,
                'grade' => $hadith->grade,
                'book' => $hadith->book ? [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name' => $hadith->book->name_en
                ] : null,
                'chapter' => $hadith->chapter ? [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name' => $hadith->chapter->name_en
                ] : null,
                'translations' => $hadith->translations->map(function($translation) {
                    return [
                        'language' => $translation->localization_code,
                        'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                        'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                        'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                    ];
                })
            ];
        });

        return $this->successResponse($formattedHadiths, [
            'category' => [
                'id' => (string) $category->id,
                'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en
            ],
            'total' => $hadiths->total(),
            'per_page' => $hadiths->perPage(),
            'current_page' => $hadiths->currentPage(),
            'last_page' => $hadiths->lastPage()
        ]);
    }

    /**
     * Get root categories
     */
    public function rootCategories(Request $request): JsonResponse
    {
        $language = $request->query('language', 'en');

        $categories = Category::whereNull('parent_id')
            ->withCount('hadiths')
            ->get();

        $formattedCategories = $categories->map(function($category) use ($language) {
            return [
                'id' => (string) $category->id,
                'parent_id' => null,
                'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en,
                'hadith_count' => (string) $category->hadiths_count
            ];
        });

        return $this->successResponse($formattedCategories, [
            'total' => $categories->count()
        ]);
    }

    /**
     * HadeethEnc compatible: List hadiths
     */
    public function hadeethsList(Request $request): JsonResponse
    {
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

        $hadithQuery = Hadith::whereHas('categories', fn($q) => $q->where('category_id', $categoryId))
            ->with(['translations']);

        $paginator = $hadithQuery->paginate($perPage, ['*'], 'page', $page);

        $data = $paginator->map(function($hadith) use ($language) {
            $translation = $hadith->translations->where('localization_code', $language)->first()
                ?: $hadith->translations->where('localization_code', 'en')->first();

            $title = $translation->translation_text ?? $hadith->arabic_text ?? '';

            $availableTranslations = $hadith->translations->pluck('localization_code')->unique()->values()->all();
            if (!in_array('ar', $availableTranslations)) {
                array_unshift($availableTranslations, 'ar');
            }

            return [
                'id' => (string) $hadith->id,
                'title' => mb_substr($title, 0, 200),
                'translations' => $availableTranslations
            ];
        });

        return $this->successResponse($data, [
            'current_page' => (string) $paginator->currentPage(),
            'last_page' => $paginator->lastPage(),
            'total_items' => $paginator->total(),
            'per_page' => (string) $paginator->perPage(),
            'category' => [
                'id' => (string) $category->id,
                'title' => $language === 'ar' && $category->name_ar ? $category->name_ar : $category->name_en
            ]
        ]);
    }

    /**
     * HadeethEnc compatible: Get single hadith
     */
    public function hadeethOne(Request $request): JsonResponse
    {
        $hadeethId = $request->query('id');
        $language = $request->query('language', 'en');

        if (!$hadeethId) {
            return $this->errorResponse('id parameter is required', null, 400);
        }

        $hadith = Hadith::with(['book', 'chapter', 'translations'])->find($hadeethId);

        if (!$hadith || !$hadith->book) {
            return $this->notFoundResponse('Hadith or associated book not found');
        }

        $categoryIds = DB::table('hadith_category')
            ->where('hadith_id', $hadeethId)
            ->pluck('category_id')
            ->map(fn($id) => (string) $id)
            ->all();

        $availableTranslations = $hadith->translations
            ->pluck('localization_code')
            ->unique()
            ->values()
            ->all();
        if (!in_array('ar', $availableTranslations)) {
            array_unshift($availableTranslations, 'ar');
        }

        $response = [
            'id' => (string) $hadith->id,
            'title' => '',
            'hadeeth' => '',
            'attribution' => $language === 'ar' && $hadith->book->name_ar ? $hadith->book->name_ar : $hadith->book->name_en,
            'grade' => $hadith->grade ?: 'Not graded',
            'explanation' => '',
            'hints' => [],
            'categories' => $categoryIds,
            'translations' => $availableTranslations,
            'references' => [],
        ];

        $arabicText = $hadith->arabic_text ?: '';
        $response['hadeeth_ar'] = $arabicText;
        $response['attribution_ar'] = $hadith->book->name_ar ?? '';

        $translation = $hadith->translations->where('localization_code', $language)->first()
            ?: $hadith->translations->where('localization_code', 'en')->first();

        if ($language === 'ar' || !$translation) {
            $response['title'] = mb_substr($arabicText, 0, 100);
            $response['hadeeth'] = $arabicText;
            $response['explanation'] = '';
        } else {
            $translationText = $translation->translation_text ?: '';
            $response['title'] = mb_substr($translationText, 0, 100);
            $response['hadeeth'] = $translationText;
            $response['explanation'] = $translation->explanation ?? '';
            $response['hints'] = $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : [];
        }

        $references = $hadith->references ? (is_string($hadith->references) ? json_decode($hadith->references, true) : $hadith->references) : [];
        if (is_array($references)) {
            $response['references'] = array_values(array_filter($references));
        }

        return $this->successResponse(['hadith' => $response]);
    }

    /**
     * Get hadiths by topic
     */
    public function topicHadiths($topic): JsonResponse
    {
        $language = request()->query('language', 'en');
        $perPage = (int) request()->query('per_page', 20);
        $page = (int) request()->query('page', 1);

        $chapters = Chapter::where('name_en', 'LIKE', "%{$topic}%")
            ->orWhere('name_ar', 'LIKE', "%{$topic}%")
            ->pluck('id');

        if ($chapters->isEmpty()) {
            return $this->successResponse([], [
                'topic' => $topic,
                'chapters_found' => 0,
                'total' => 0,
                'per_page' => $perPage,
                'current_page' => $page,
                'last_page' => 1
            ]);
        }

        $hadiths = Hadith::whereIn('chapter_id', $chapters)
            ->select('id', 'book_id', 'chapter_id', 'hadith_number', 'arabic_text', 'grade')
            ->with(['book:id,code,name_en,name_ar', 'chapter:id,chapter_no,name_en,name_ar', 'translations'])
            ->paginate($perPage, ['*'], 'page', $page);

        $formattedHadiths = $hadiths->map(function($hadith) {
            return [
                'id' => (string) $hadith->id,
                'hadith_number' => $hadith->hadith_number,
                'arabic_text' => $hadith->arabic_text,
                'grade' => $hadith->grade,
                'book' => $hadith->book ? [
                    'id' => $hadith->book->id,
                    'code' => $hadith->book->code,
                    'name' => $hadith->book->name_en
                ] : null,
                'chapter' => $hadith->chapter ? [
                    'id' => $hadith->chapter->id,
                    'chapter_no' => $hadith->chapter->chapter_no,
                    'name' => $hadith->chapter->name_en
                ] : null,
                'translations' => $hadith->translations->map(function($translation) {
                    return [
                        'language' => $translation->localization_code,
                        'text' => $this->localizeNumbers($translation->translation_text, $translation->localization_code),
                        'explanation' => $this->localizeNumbers($translation->explanation, $translation->localization_code),
                        'hints' => $translation->hints ? (is_string($translation->hints) ? json_decode($translation->hints, true) : $translation->hints) : []
                    ];
                })
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
        $book = Book::with(['chapters' => function($query) {
            $query->select('id', 'book_id', 'chapter_no', 'name_en', 'total_hadith')
                    ->orderBy('chapter_no');
        }])->find($id);

        if (!$book) {
            return response()->json(['error' => 'Book not found'], 404);
        }

        return view('hadith.book-simple', [
            'book' => $book,
            'chapters' => $book->chapters
        ]);
    }
}