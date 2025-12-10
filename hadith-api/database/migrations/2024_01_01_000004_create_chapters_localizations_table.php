<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('chapters_localizations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('chapter_id')->constrained('chapters')->onDelete('cascade');
            $table->integer('localization_id');
            $table->string('localization_code', 10);
            $table->string('name', 255);
            $table->string('slug', 512);
            $table->timestamps();
            $table->softDeletes();
            
            $table->index('chapter_id');
            $table->index('localization_code');
            $table->index('slug');
            $table->unique(['chapter_id', 'localization_code'], 'idx_chapters_loc_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('chapters_localizations');
    }
};