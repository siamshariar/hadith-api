<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
class CategoryLocalization extends Model
{
    use HasFactory;

    protected $fillable = [
        'category_id',
        'localization_code',
        'name'
    ];

    public function category()
    {
        return $this->belongsTo(Category::class);
    }
}
