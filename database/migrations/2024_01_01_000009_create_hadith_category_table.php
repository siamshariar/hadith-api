<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('hadith_category', function (Blueprint $table) {
            $table->foreignId('hadith_id')->constrained('hadiths')->onDelete('cascade');
            $table->foreignId('category_id')->constrained('categories')->onDelete('cascade');
            
            $table->primary(['hadith_id', 'category_id']);
            $table->index('category_id');
            $table->index('hadith_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('hadith_category');
    }
};
