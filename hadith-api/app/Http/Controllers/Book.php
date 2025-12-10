<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class Book extends Model
{
    use SoftDeletes;

    protected $fillable = [
        'code', 'name_en', 'name_ar', 'total_hadith', 'slug'
    ];

    public function chapters()
    {
        return $this->hasMany(Chapter::class);
    }

    public function hadiths()
    {
        return $this->hasMany(Hadith::class);
    }

    public function localizations()
    {
        return $this->hasMany(BookLocalization::class);
    }
}