<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class CategoryLocalization extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'category_id',
        'localization_code',
        'name',
        'slug'
    ];

    public function category()
    {
        return $this->belongsTo(Category::class);
    }
}
