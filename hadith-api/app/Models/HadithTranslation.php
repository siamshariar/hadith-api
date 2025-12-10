<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
class HadithTranslation extends Model
{
    use HasFactory;

    protected $fillable = [
        'hadith_id',
        'localization_id',
        'localization_code',
        'translation_text',
        'explanation',
        'hints'
    ];

    protected $casts = [
        'hints' => 'array'
    ];

    public function hadith()
    {
        return $this->belongsTo(Hadith::class);
    }
}