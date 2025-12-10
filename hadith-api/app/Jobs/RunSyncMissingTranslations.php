<?php

namespace App\Jobs;

use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;
use Symfony\Component\Process\Process;

class RunSyncMissingTranslations implements ShouldQueue
{
    use InteractsWithQueue, Queueable, SerializesModels;

    public $tries = 1;
    protected $options;

    public function __construct(array $options = [])
    {
        $this->options = $options;
    }

    public function handle()
    {
        $script = base_path('scripts/sync_missing_translations.py');
        $cmd = ['python', $script];

        foreach ($this->options as $k => $v) {
            if (is_bool($v)) {
                if ($v) $cmd[] = "--$k";
            } else {
                $cmd[] = "--$k";
                $cmd[] = (string) $v;
            }
        }

        $proc = new Process($cmd);
        $proc->setTimeout(0);
        try {
            Log::info('RunSyncMissingTranslations starting: ' . implode(' ', $cmd));
            $proc->run(function ($type, $buffer) {
                Log::info("[sync] $buffer");
            });
            Log::info('RunSyncMissingTranslations finished: ' . $proc->getExitCode() . ' ' . $proc->getExitCodeText());
        } catch (\Exception $e) {
            Log::error('RunSyncMissingTranslations error: ' . $e->getMessage());
        }
    }
}
