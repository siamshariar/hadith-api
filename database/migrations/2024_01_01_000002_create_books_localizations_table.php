<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('books_localizations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('book_id')->constrained('books')->onDelete('cascade');
            $table->integer('localization_id');
            $table->string('localization_code', 10);
            $table->string('name', 255);
            $table->string('slug', 512);
            $table->timestamps();
            $table->softDeletes();
            
            $table->index('book_id');
            $table->index('localization_code');
            $table->index('slug');
            $table->unique(['book_id', 'localization_code'], 'idx_books_loc_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('books_localizations');
    }
};
