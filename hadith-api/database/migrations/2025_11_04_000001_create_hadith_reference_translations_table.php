<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     * 
     * This creates a dedicated table for language-wise hadith references.
     * Instead of storing references in multiple places (hadiths table + hadith_translations table),
     * we now have a single source of truth for references that can be translated to any language.
     */
    public function up(): void
    {
        Schema::create('hadith_reference_translations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('hadith_id')->constrained('hadiths')->onDelete('cascade');
            $table->string('localization_code', 10); // e.g., 'en', 'bn', 'ar', 'ur', etc.
            $table->longText('references_text'); // References translated to the specific language
            $table->timestamps();
            $table->softDeletes();
            
            // Indexes for fast retrieval
            $table->index('hadith_id');
            $table->index('localization_code');
            $table->index(['hadith_id', 'localization_code']); // Most common query pattern
            $table->index('deleted_at');
            
            // Unique constraint: each hadith can have only one reference set per language
            $table->unique(['hadith_id', 'localization_code'], 'hadith_ref_translation_unique');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('hadith_reference_translations');
    }
};
