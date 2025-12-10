<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class HadithTranslation extends Model
{
    use SoftDeletes;

    protected $fillable = [
        'hadith_id', 'localization_id', 'localization_code', 'translation_text'
    ];

    public function hadith()
    {
        return $this->belongsTo(Hadith::class);
    }
}