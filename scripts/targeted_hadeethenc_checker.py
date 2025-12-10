#!/usr/bin/env python3
"""
Targeted HadeethEnc checker

Scans CSV files at `scripts/missing_translations/missing_{lang}.csv` (or a single language via --lang),
queries HadeethEnc once per id (no repeated backoff) and writes:
 - `scripts/targeted_results/found_{lang}.jsonl` (one JSON per found hadith)
 - `scripts/targeted_results/remaining_{lang}.csv` (IDs still missing)
 - `scripts/targeted_results/summary_{lang}.txt` (brief stats)

This helps stop endless retries against HadeethEnc and gives a deterministic list
to try other sources or prepare translation fallbacks.
"""
import argparse
import csv
import json
import os
import sys
import time
from urllib import request, error


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MISSING_DIR = os.path.join(BASE_DIR, 'scripts', 'missing_translations')
TARGET_DIR = os.path.join(BASE_DIR, 'scripts', 'targeted_results')
os.makedirs(TARGET_DIR, exist_ok=True)


def check_one(hadith_id: str, lang: str, timeout: int = 10):
    url = f'https://hadeethenc.com/api/v1/hadeeths/one/?id={hadith_id}&language={lang}'
    req = request.Request(url, headers={'User-Agent': 'hadith-import-checker/1.0'})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None, resp.status
            data = resp.read().decode('utf-8')
            try:
                return json.loads(data), 200
            except Exception:
                return None, 'invalid-json'
    except error.HTTPError as he:
        return None, he.code
    except error.URLError as ue:
        return None, f'urlerr:{ue.reason}'
    except Exception as e:
        return None, f'err:{e}'


def process_lang(lang: str, in_path: str):
    ids = []
    with open(in_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            ids.append(str(row[0]).strip())

    found_path = os.path.join(TARGET_DIR, f'found_{lang}.jsonl')
    remaining_path = os.path.join(TARGET_DIR, f'remaining_{lang}.csv')
    summary_path = os.path.join(TARGET_DIR, f'summary_{lang}.txt')

    found_count = 0
    missing_count = 0
    total = len(ids)

    with open(found_path, 'w', encoding='utf-8') as found_f:
        remaining_ids = []
        for i, hid in enumerate(ids, start=1):
            # single-shot check: treat 404 as permanent for this source
            data, status = check_one(hid, lang)
            if data and status == 200:
                json.dump({'id': hid, 'result': data}, found_f, ensure_ascii=False)
                found_f.write('\n')
                found_count += 1
            else:
                # not found or other error -> record to remaining
                remaining_ids.append(hid)
                missing_count += 1

            # light progress output
            if i % 100 == 0 or i == total:
                print(f'[{lang}] processed {i}/{total} — found {found_count}, remaining {missing_count}')
            # be nice to the remote API
            time.sleep(0.05)

    # write remaining ids
    with open(remaining_path, 'w', newline='', encoding='utf-8') as rem_f:
        writer = csv.writer(rem_f)
        for rid in remaining_ids:
            writer.writerow([rid])

    with open(summary_path, 'w', encoding='utf-8') as s_f:
        s_f.write(f'language: {lang}\n')
        s_f.write(f'total_checked: {total}\n')
        s_f.write(f'found: {found_count}\n')
        s_f.write(f'remaining: {missing_count}\n')
        s_f.write(f'found_path: {found_path}\n')
        s_f.write(f'remaining_path: {remaining_path}\n')

    return {'lang': lang, 'total': total, 'found': found_count, 'remaining': missing_count,
            'found_path': found_path, 'remaining_path': remaining_path}


def main():
    p = argparse.ArgumentParser(description='Targeted HadeethEnc checker for missing translations')
    p.add_argument('--lang', '-l', help='Language code to process (e.g. vi). If omitted, process all CSVs in missing_translations')
    args = p.parse_args()

    targets = []
    if args.lang:
        in_file = os.path.join(MISSING_DIR, f'missing_{args.lang}.csv')
        if not os.path.isfile(in_file):
            print(f'ERROR: missing file {in_file}', file=sys.stderr)
            sys.exit(2)
        targets.append((args.lang, in_file))
    else:
        for fname in os.listdir(MISSING_DIR):
            if fname.startswith('missing_') and fname.endswith('.csv'):
                lang = fname[len('missing_'):-len('.csv')]
                targets.append((lang, os.path.join(MISSING_DIR, fname)))

    overall = []
    for lang, path in targets:
        print(f'Processing {lang} from {path} ...')
        res = process_lang(lang, path)
        overall.append(res)

    print('\nSummary:')
    for r in overall:
        print(f"{r['lang']}: checked={r['total']} found={r['found']} remaining={r['remaining']}")


if __name__ == '__main__':
    main()
