<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('books', function (Blueprint $table) {
            $table->id();
            $table->string('code', 50)->unique()->comment('e.g: bukhari, muslim');
            $table->string('name_en', 255);
            $table->string('name_ar', 255)->nullable();
            $table->integer('total_hadith')->default(0);
            $table->string('slug', 512);
            $table->timestamps();
            $table->softDeletes();
            
            $table->index('code');
            $table->index('slug');
            $table->index('deleted_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('books');
    }
};