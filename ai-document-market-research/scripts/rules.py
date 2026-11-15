#!/usr/bin/env python3
"""Shared mechanical rules for the research ledgers (research tooling only).

- registrable domain of a URL
- which pages count as "vendor-written" for a competitor candidate: decided by the page's
  host (the candidate's registered official URL plus the reviewed alias table
  registry/competitor_official_domains.csv), never by a worker's label
- minimum evidence rules for a quoted passage
"""
from __future__ import annotations
import csv
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

SECOND_LEVEL = ('co.jp', 'ac.jp', 'go.jp', 'or.jp', 'ne.jp', 'lg.jp', 'ed.jp', 'gr.jp', 'co.uk', 'ac.uk', 'gov.uk', 'org.uk', 'com.au', 'edu.au',
                'gov.au', 'co.kr', 'com.cn', 'edu.cn', 'co.nz', 'com.sg', 'edu.sg', 'co.in', 'ac.in', 'com.br', 'com.tw', 'edu.tw')
# hosts where many unrelated publishers share one registrable domain: the origin is the publisher, not the host
MULTI_ORIGIN_HOSTS = ('arxiv.org', 'prtimes.jp', 'digitalpr.jp', 'github.com', 'github.io', 'note.com', 'reddit.com', 'youtube.com', 'medium.com',
                      'qiita.com', 'zenn.dev', 'kyodonewsprwire.jp', 'researchgate.net', 'ssrn.com', 'nber.org', 'jst.go.jp', 'apple.com',
                      'google.com', 'acm.org', 'petsymposium.org', 'usenix.org', 'openreview.net', 'aclanthology.org', 'sciencedirect.com',
                      'springer.com', 'nature.com', 'mdpi.com', 'tandfonline.com', 'wiley.com', 'biorxiv.org', 'nih.gov', 'jsdelivr.net',
                      'semanticscholar.org', 'substack.com', 'hatenablog.com', 'speakerdeck.com', 'slideshare.net', 'ieee.org', 'cvf.com',
                      'thecvf.com', 'mlr.press', 'neurips.cc', 'huggingface.co', 'ac.jp', 'frontiersin.org', 'plos.org', 'sagepub.com',
                      'oup.com', 'cambridge.org', 'jmir.org', 'elsevier.com', 'ceur-ws.org', 'osf.io', 'zenodo.org', 'ipsj.or.jp', 'nii.ac.jp',
                      'wordpress.com', 'blogspot.com', 'linkedin.com', 'x.com', 'twitter.com', 'facebook.com', 'producthunt.com')
# registrable domains shared by unrelated tenants: an official-URL candidate on one of these only vouches for its own host / path
SHARED_HOSTS = ('github.io', 'github.com', 'apple.com', 'notion.site', 'substack.com', 'medium.com', 'wordpress.com', 'blogspot.com', 'web.app', 'vercel.app', 'netlify.app')
MIN_QUOTE = 16      # characters after removing whitespace
MIN_QUOTE_VALUE = 8  # a table cell backing a figure may be short, but the figure itself must be in it
# user-written areas on a vendor's own domain are not vendor-written material
UGC_HOST_PREFIXES = ('community.', 'communities.', 'forum.', 'forums.', 'answers.', 'discuss.', 'discussion.', 'discussions.', 'feedback.', 'ideas.', 'techcommunity.', 'uservoice.')
UGC_PATH_PREFIXES = ('/community', '/forum', '/answers/questions', '/discussions', '/t5/')
MIN_PAGE_CHARS = 400


def squash(s: str) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s or ''))


def host_of(u: str) -> str:
    return urlsplit(u.strip()).netloc.lower().split(':')[0].removeprefix('www.')


def domain(u: str) -> str:
    host = urlsplit(u).netloc.lower().split(':')[0]
    parts = host.split('.')
    if len(parts) >= 3 and '.'.join(parts[-2:]) in SECOND_LEVEL:
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:]) if len(parts) >= 2 else host


def under(d: str, h: str) -> bool:
    """True if host/domain d is h or a sub-domain of h (label boundary, not a plain suffix)."""
    return d == h or d.endswith('.' + h)


def multi_origin(d: str) -> bool:
    return any(under(d, h) for h in MULTI_ORIGIN_HOSTS if '/' not in h)


def official_rules(reg: Path, comps: list[dict] | None = None) -> dict[str, list[tuple[str, str]]]:
    """competitor_id -> [(host, path_prefix)] of pages treated as vendor-written."""
    if comps is None:
        with (reg / 'competitor_candidates.csv').open(encoding='utf-8-sig', newline='') as f:
            comps = list(csv.DictReader(f))
    rules: dict[str, list[tuple[str, str]]] = {}
    for c in comps:
        u = (c.get('official_url_candidate') or '').strip()
        r = []
        if u.startswith(('http://', 'https://')):
            d = domain(u)
            if any(under(d, s) for s in SHARED_HOSTS):
                r.append((host_of(u), ''))      # only this tenant's host
            else:
                r.append((d, ''))
        rules[c['competitor_id']] = r
    p = reg / 'competitor_official_domains.csv'
    if p.exists():
        with p.open(encoding='utf-8-sig', newline='') as f:
            for x in csv.DictReader(f):
                m = (x.get('match') or '').strip().lower()
                if not m or x.get('competitor_id') not in rules:
                    continue
                h, _, path = m.partition('/')
                rules[x['competitor_id']].append((h.removeprefix('www.'), '/' + path if path else ''))
    return rules


def is_official(rules: dict, cid: str, url: str) -> bool:
    if not str(url).startswith(('http://', 'https://')):
        return False
    s = urlsplit(url.strip())
    h = s.netloc.lower().split(':')[0].removeprefix('www.')
    if h.startswith(UGC_HOST_PREFIXES) or s.path.lower().startswith(UGC_PATH_PREFIXES):
        return False
    return any(under(h, rh) and (not rp or s.path.lower().startswith(rp)) for rh, rp in rules.get(cid, []))


def number_tokens(s: str) -> list[str]:
    return re.findall(r'\d+(?:\.\d+)?', unicodedata.normalize('NFKC', str(s or '')).replace(',', ''))


def value_in_quote(value: str, quote: str) -> bool:
    """A reported figure must be visible in its quote. Values without digits are qualitative and pass."""
    toks = number_tokens(value)
    if not toks:
        return True
    q = unicodedata.normalize('NFKC', quote or '').replace(',', '')
    return any(t in q for t in toks)
