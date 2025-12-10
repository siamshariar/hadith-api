<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class Hadith extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'book_id',
        'chapter_id',
        'hadith_number',
        'arabic_text',
        'grade',
        'explanation',
        'hints',
        'word_meanings',
        'references'
    ];

    protected $casts = [
        'hints' => 'array',
        'word_meanings' => 'array',
        'references' => 'array'
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

    public function referenceTranslations()
    {
        return $this->hasMany(HadithReferenceTranslation::class);
    }

    public function categories()
    {
        return $this->belongsToMany(Category::class, 'hadith_category');
    }
}