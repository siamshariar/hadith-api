<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class HadithReferenceTranslation extends Model
{
    use SoftDeletes;

    protected $table = 'hadith_reference_translations';

    protected $fillable = [
        'hadith_id',
        'localization_code',
        'references_text'
    ];

    protected $casts = [
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
        'deleted_at' => 'datetime'
    ];

    /**
     * Get the hadith that owns this reference translation.
     */
    public function hadith()
    {
        return $this->belongsTo(Hadith::class);
    }

    /**
     * Get all reference translations for a specific hadith.
     */
    public static function getByHadithAndLanguage($hadithId, $languageCode)
    {
        return self::where('hadith_id', $hadithId)
            ->where('localization_code', $languageCode)
            ->first();
    }

    /**
     * Get all available reference translations for a hadith.
     */
    public static function getByHadith($hadithId)
    {
        return self::where('hadith_id', $hadithId)
            ->orderBy('localization_code')
            ->get();
    }
}
