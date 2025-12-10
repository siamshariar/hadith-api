<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('hadiths', function (Blueprint $table) {
            // Add new columns if they don't exist
            if (!Schema::hasColumn('hadiths', 'hadeeth_intro_ar')) {
                $table->longText('hadeeth_intro_ar')->nullable()->after('arabic_text');
            }
            if (!Schema::hasColumn('hadiths', 'attribution_ar')) {
                $table->text('attribution_ar')->nullable()->after('grade');
            }
            if (!Schema::hasColumn('hadiths', 'categories')) {
                $table->json('categories')->nullable()->after('references');
            }
            if (!Schema::hasColumn('hadiths', 'available_translations')) {
                $table->json('available_translations')->nullable()->after('categories');
            }
        });
    }

    public function down(): void
    {
        Schema::table('hadiths', function (Blueprint $table) {
            $table->dropColumn(['hadeeth_intro_ar', 'attribution_ar', 'categories', 'available_translations']);
        });
    }
};
