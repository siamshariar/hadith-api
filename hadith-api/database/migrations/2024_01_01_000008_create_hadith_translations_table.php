<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('hadith_translations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('hadith_id')->constrained('hadiths')->onDelete('cascade');
            $table->integer('localization_id');
            $table->string('localization_code', 10);
            $table->longText('translation_text');
            $table->timestamps();
            $table->softDeletes();
            
            $table->index('hadith_id');
            $table->index('localization_code');
            $table->index(['hadith_id', 'localization_code']);
            $table->index('deleted_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('hadith_translations');
    }
};