<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('hadith_translations', function (Blueprint $table) {
            // Add new columns if they don't exist
            if (!Schema::hasColumn('hadith_translations', 'hadeeth_intro')) {
                $table->longText('hadeeth_intro')->nullable()->after('translation_text');
            }
            if (!Schema::hasColumn('hadith_translations', 'attribution')) {
                $table->text('attribution')->nullable()->after('hadeeth_intro');
            }
        });
    }

    public function down(): void
    {
        Schema::table('hadith_translations', function (Blueprint $table) {
            $table->dropColumn(['hadeeth_intro', 'attribution']);
        });
    }
};
