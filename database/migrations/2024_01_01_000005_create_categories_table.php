<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('categories', function (Blueprint $table) {
            $table->id();
            $table->foreignId('parent_id')->nullable()->constrained('categories')->onDelete('cascade');
            $table->string('name_en', 255);
            $table->string('name_ar', 255)->nullable();
            $table->string('slug', 512);
            $table->timestamps();
            $table->softDeletes();
            
            $table->index('parent_id');
            $table->index('slug');
            $table->index('deleted_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('categories');
    }
};
