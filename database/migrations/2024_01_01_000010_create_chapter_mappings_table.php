<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('chapter_mappings', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_chapter_id')->constrained('chapters')->onDelete('cascade');
            $table->foreignId('target_chapter_id')->constrained('chapters')->onDelete('cascade');
            $table->enum('mapping_type', ['exact', 'partial', 'manual'])->default('manual');
            $table->decimal('confidence_level', 3, 2)->default(1.00);
            $table->text('notes')->nullable();
            $table->timestamps();
            
            $table->index(['source_chapter_id', 'target_chapter_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('chapter_mappings');
    }
};
