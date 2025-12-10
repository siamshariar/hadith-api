<?php
namespace App\Console\Commands;

use Illuminate\Console\Command;

class SyncMissingTranslations extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'sync:missing-translations {--lang=} {--books=} {--limit=} {--dry-run} {--overwrite} {--confirm} {--source=} {--import-file=} {--sample=} {--languages=} {--queue}';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Synchronize missing translations using scripts/sync_missing_translations.py';

    /**
     * Execute the console command.
     */
    public function handle()
    {
        $lang = $this->option('lang') ?: 'bn';
        $books = $this->option('books');
        $limit = $this->option('limit');
        $dry = $this->option('dry-run') ? '--dry-run' : '';
        $import_file = $this->option('import-file');
        $sample = $this->option('sample');
        $languages = $this->option('languages');
        $source = $this->option('source') ?: 'fawaz,hadeethenc,alquranbd';

        $queue = $this->option('queue');
        $script = base_path('scripts/sync_missing_translations.py');
        if (!file_exists($script)) {
            $this->error("Script not found: {$script}");
            return 1;
        }

        // Build cmd
        $cmd = [
            PHP_BINARY, // placeholder for correct interpreter name, we'll call python in shell
        ];
        // prefer system python
        $cmd = ['python', $script, '--lang', $lang, '--source', $source];
        if ($books) $cmd = array_merge($cmd, ['--books', $books]);
        if ($import_file) $cmd = array_merge($cmd, ['--import-file', $import_file]);
        if ($sample) $cmd = array_merge($cmd, ['--sample', $sample]);
        if ($languages) $cmd = array_merge($cmd, ['--languages', $languages]);
        if ($limit) $cmd = array_merge($cmd, ['--limit', $limit]);
        if ($this->option('overwrite')) $cmd[] = '--overwrite';
        if ($this->option('confirm')) $cmd[] = '--confirm';
        if ($dry) $cmd[] = $dry;

        $this->info('Running: ' . implode(' ', $cmd));

        // Optionally dispatch to queue for background processing
        if ($queue) {
            $options = [];
            if ($lang) $options['lang'] = $lang;
            if ($books) $options['books'] = $books;
            if ($limit) $options['limit'] = $limit;
            if ($import_file) $options['import-file'] = $import_file;
            if ($sample) $options['sample'] = $sample;
            if ($languages) $options['languages'] = $languages;
            if ($source) $options['source'] = $source;
            if ($dry) $options['dry-run'] = true;
            if ($this->option('overwrite')) $options['overwrite'] = true;
            if ($this->option('confirm')) $options['confirm'] = true;

            \App\Jobs\RunSyncMissingTranslations::dispatch($options);
            $this->info('Sync dispatched to queue');
            return 0;
        }

        // Execute synchronously in background
        $descriptorspec = [
            0 => ['pipe', 'r'],
            1 => ['pipe', 'w'],
            2 => ['pipe', 'w']
        ];
        $process = proc_open(implode(' ', $cmd), $descriptorspec, $pipes, base_path());

        if (is_resource($process)) {
            $output = stream_get_contents($pipes[1]);
            $err = stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);

            $status = proc_get_status($process);
            proc_close($process);

            $this->info('Command finished.');
            if ($output) $this->line($output);
            if ($err) $this->error($err);
            return $status['exitcode'] ?? 0;
        }

        $this->error('Failed to start process');
        return 1;
    }

                // no-op (overwrite/confirm passed earlier)
}
