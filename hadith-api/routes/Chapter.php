<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class Chapter extends Model
{
    use SoftDeletes;

    protected $fillable = [
        'book_id', 'chapter_no', 'name_en', 'name_ar', 'total_hadith', 'slug'
    ];

    public function book()
    {
        return $this->belongsTo(Book::class);
    }

    public function hadiths()
    {
        return $this->hasMany(Hadith::class);
    }

    public function localizations()
    {
        return $this->hasMany(ChapterLocalization::class);
    }
}