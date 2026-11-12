"""Integrity tests for the live evidence ledger.

They do not prove that a source is true. They make sure the ledger cannot
silently contain accepted-but-unopened sources, untraceable numbers, verified
competitors without evidence, screenshots in Git, or application code.
"""
import csv
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / 'registry'


def rows(name):
    with (REG / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def ids(value):
    return {x.strip() for x in (value or '').split(';') if x.strip()}


class LiveLedgerTests(unittest.TestCase):
    def setUp(self):
        self.topics = {r['topic_id']: r['axis_id'] for r in rows('research_axes.csv')}
        if (REG / 'additional_axes.csv').exists():
            self.topics.update({r['topic_id']: r['axis_id'] for r in rows('additional_axes.csv')})
        self.sources = rows('source_evidence.csv')
        self.accepted = {r['source_id'] for r in self.sources if r['is_accepted'] == 'yes'}

    def test_accepted_sources_were_opened_and_are_traceable(self):
        for r in self.sources:
            if r['is_accepted'] != 'yes':
                continue
            self.assertIn(r['verified_state'], ('DIRECT_ORIGINAL', 'VERIFIED_SECONDARY'), r['source_id'])
            self.assertTrue(r['url'].startswith(('https://', 'http://')), r['source_id'])
            self.assertIn(r['topic_id'], self.topics, r['source_id'])
            self.assertEqual(r['axis_id'], self.topics[r['topic_id']], r['source_id'])
            for k in ('origin_group_id', 'publisher', 'checked_at', 'claim_text', 'page_or_section'):
                self.assertTrue(r[k].strip() and r[k] != 'UNKNOWN', f"{r['source_id']}: {k}")

    def test_source_ids_unique(self):
        all_ids = [r['source_id'] for r in self.sources]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_search_log_rows_are_dated_and_mapped(self):
        log = rows('search_log.csv')
        qids = {r['query_id'] for r in log}
        self.assertEqual(len(qids), len(log))
        for r in log:
            self.assertTrue(r['topic_id'] in self.topics, r['query_id'])
            self.assertRegex(r['searched_at'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', r['query_id'])
            self.assertTrue(r['platform'].strip() and r['query'].strip(), r['query_id'])
            m = re.search(r'same_action_as=(Q\d+)', r['notes'])
            if m:
                self.assertIn(m.group(1), qids, r['query_id'])

    def test_verified_competitors_cite_accepted_sources(self):
        for r in rows('competitor_candidates.csv'):
            if r['verification_state'] == 'VERIFIED_OFFICIAL':
                cited = ids(r['sources'])
                self.assertTrue(cited, r['competitor_id'])
                self.assertTrue(cited <= self.accepted, f"{r['competitor_id']}: {cited - self.accepted}")

    def test_numbers_are_traceable_and_classified(self):
        allowed = {'OBSERVED', 'MODEL_BASED', 'MIXED', 'ASSUMPTION_ONLY', 'NON_IDENTIFIABLE'}
        for r in rows('quant_results.csv'):
            self.assertIn(r['evidence_category'], allowed, r['result_id'])
            if r['evidence_category'] in ('OBSERVED', 'MODEL_BASED', 'MIXED'):
                self.assertTrue(ids(r['source_ids']) and ids(r['source_ids']) <= self.accepted, r['result_id'])
            if r['evidence_category'] in ('MODEL_BASED', 'MIXED'):
                self.assertTrue(r['model_id'].strip(), r['result_id'])
            if r['evidence_category'] == 'NON_IDENTIFIABLE':
                self.assertFalse(re.fullmatch(r'[\d.]+', r['estimate'].strip()), r['result_id'])

    def test_claims_cite_accepted_sources(self):
        for r in rows('product_claims.csv'):
            self.assertTrue(ids(r['source_ids']) <= self.accepted, r['claim_id'])

    def test_no_screenshots_or_app_code_in_git(self):
        try:
            out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '.'], capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest('not a git checkout')
        tracked = out.splitlines()
        self.assertFalse([f for f in tracked if re.search(r'\.(png|jpe?g|gif|webp|heic)$', f, re.I)], 'images must not be committed')
        app_like = re.compile(r'\.(html?|css|jsx?|tsx?|vue|svelte|swift|kt|dart|ya?ml|toml|dockerfile)$', re.I)
        self.assertFalse([f for f in tracked if app_like.search(f)], 'no app / UI / deployment files in the research folder')


if __name__ == '__main__':
    unittest.main()
