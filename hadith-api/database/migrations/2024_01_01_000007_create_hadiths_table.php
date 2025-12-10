<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('hadiths', function (Blueprint $table) {
            $table->id();
            $table->foreignId('book_id')->constrained('books')->onDelete('cascade');
            $table->foreignId('chapter_id')->constrained('chapters')->onDelete('cascade');
            $table->string('hadith_number', 50);
            $table->longText('arabic_text');
            $table->string('grade', 100)->nullable();
            $table->timestamps();
            $table->softDeletes();
            
            $table->index('book_id');
            $table->index('chapter_id');
            $table->index('hadith_number');
            $table->index(['book_id', 'chapter_id']);
            $table->index(['book_id', 'hadith_number']);
            $table->index('deleted_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('hadiths');
    }
};