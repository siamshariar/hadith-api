<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('chapters', function (Blueprint $table) {
            $table->id();
            $table->foreignId('book_id')->constrained('books')->onDelete('cascade');
            $table->integer('chapter_no');
            $table->string('name_en', 255);
            $table->string('name_ar', 255)->nullable();
            $table->integer('total_hadith')->default(0);
            $table->string('slug', 512);
            $table->timestamps();
            $table->softDeletes();
            
            $table->index('book_id');
            $table->index(['book_id', 'chapter_no']);
            $table->index('slug');
            $table->index('deleted_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('chapters');
    }
};