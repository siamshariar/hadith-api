<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
class Category extends Model
{
    use HasFactory;

    protected $fillable = [
        'name_en',
        'name_ar',
        'parent_id'
    ];

    public function parent()
    {
        return $this->belongsTo(Category::class, 'parent_id');
    }

    public function children()
    {
        return $this->hasMany(Category::class, 'parent_id');
    }

    public function hadiths()
    {
        return $this->belongsToMany(Hadith::class, 'hadith_category');
    }

    public function localizations()
    {
        return $this->hasMany(CategoryLocalization::class);
    }

    public function getLocalizedName($languageCode)
    {
        // Try to get from localizations table
        $localization = $this->localizations()
            ->where('localization_code', $languageCode)
            ->first();
        
        if ($localization) {
            return $localization->name;
        }
        
        // Fallback to main table fields
        if ($languageCode === 'ar' && $this->name_ar) {
            return $this->name_ar;
        }
        
        // Default to English
        return $this->name_en;
    }
}