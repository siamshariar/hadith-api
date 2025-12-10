<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('category_localizations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('category_id')->constrained('categories')->onDelete('cascade');
            $table->string('localization_code', 10);
            $table->string('name', 255);
            $table->string('slug', 512);
            $table->timestamps();
            $table->softDeletes();
            
            $table->index('category_id');
            $table->index('localization_code');
            $table->index('slug');
            $table->unique(['category_id', 'localization_code'], 'idx_cat_loc_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('category_localizations');
    }
};
