<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
class Book extends Model
{
    use HasFactory;

    protected $fillable = [
        'code',
        'name_en',
        'name_ar',
        'total_hadith'
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