<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class Hadith extends Model
{
    use SoftDeletes;

    protected $fillable = [
        'book_id', 'chapter_id', 'hadith_number', 'arabic_text', 'grade'
    ];

    public function book()
    {
        return $this->belongsTo(Book::class);
    }

    public function chapter()
    {
        return $this->belongsTo(Chapter::class);
    }

    public function translations()
    {
        return $this->hasMany(HadithTranslation::class);
    }

    public function categories()
    {
        return $this->belongsToMany(Category::class, 'hadith_category');
    }
}