<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        // Add fields to hadiths table (for Arabic content)
        Schema::table('hadiths', function (Blueprint $table) {
            $table->longText('explanation')->nullable()->after('grade');
            $table->json('hints')->nullable()->after('explanation');
            $table->json('word_meanings')->nullable()->after('hints');
            $table->json('references')->nullable()->after('word_meanings');
        });

        // Add fields to hadith_translations table (for translated content)
        Schema::table('hadith_translations', function (Blueprint $table) {
            $table->longText('explanation')->nullable()->after('translation_text');
            $table->json('hints')->nullable()->after('explanation');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('hadiths', function (Blueprint $table) {
            $table->dropColumn(['explanation', 'hints', 'word_meanings', 'references']);
        });

        Schema::table('hadith_translations', function (Blueprint $table) {
            $table->dropColumn(['explanation', 'hints']);
        });
    }
};
