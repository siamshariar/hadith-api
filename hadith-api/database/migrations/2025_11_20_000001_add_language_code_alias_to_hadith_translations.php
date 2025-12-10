<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        if (!Schema::hasColumn('hadith_translations', 'language_code')) {
            Schema::table('hadith_translations', function (Blueprint $table) {
                $table->string('language_code', 10)->nullable()->after('localization_code');
            });

            // Backfill from localization_code
            DB::table('hadith_translations')
                ->whereNull('language_code')
                ->update(['language_code' => DB::raw('localization_code')]);

            Schema::table('hadith_translations', function (Blueprint $table) {
                $table->index('language_code');
                $table->index(['hadith_id', 'language_code']);
            });
        }
    }

    public function down(): void
    {
        if (Schema::hasColumn('hadith_translations', 'language_code')) {
            Schema::table('hadith_translations', function (Blueprint $table) {
                $table->dropIndex(['language_code']);
                $table->dropIndex(['hadith_id', 'language_code']);
                $table->dropColumn('language_code');
            });
        }
    }
};
