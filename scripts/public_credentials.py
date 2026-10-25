"""Mask owner credential identifiers in public output, preserving trade facts.

This is a final-output privacy pass, not a PDF redactor. Original certificates
must never enter the public build. Manufacturer manual/model numbers deliberately
remain untouched. No identifier value is returned in the diagnostics.
"""
from __future__ import annotations

import json
import html
from pathlib import PurePosixPath
import re

MASK = '****'
TEXT_SUFFIXES = {'.html', '.json', '.js', '.css', '.php', '.txt', '.xml', '.svg', '.md'}
_SLASH = r'(?:/|\\/|&#0*47;|&#x0*2[fF];)'
_CREDENTIAL = re.compile(
    r'(?<![A-Z0-9])YB\d{4}\s*' + _SLASH + r'\s*\d{2}UY\d{4}-\d{1,2}\s*'
    + _SLASH + r'\s*\d{2}\s*' + _SLASH + r'\s*\d{1,12}(?![A-Z0-9])',
    re.IGNORECASE,
)


def mask_text(text: str) -> tuple[str, int]:
    """Expose only the last four numeric digits of a certificate identifier.

    Normalize entity/escaped delimiters first: digits in ``&#47;`` describe a
    slash and must never be mistaken for part of the document number.
    """
    def partial(match: re.Match) -> str:
        identifier = html.unescape(match.group(0)).replace('\\/', '/')
        return MASK + ''.join(re.findall(r'[0-9]', identifier))[-4:]
    return _CREDENTIAL.subn(partial, text)


def _mask_json(value):
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, list):
        result, count = [], 0
        for item in value:
            masked, occurrences = _mask_json(item)
            result.append(masked)
            count += occurrences
        return result, count
    if isinstance(value, dict):
        result, count = {}, 0
        for key, item in value.items():
            masked, occurrences = _mask_json(item)
            result[key] = masked
            count += occurrences
        return result, count
    return value, 0


def mask_public_credentials(files: dict[str, bytes]) -> dict:
    """Run after all generators and URL rewriting, before build-info hashing.

    JSON is decoded before checking strings so unicode-escaped identifiers cannot
    survive only to be revealed when a client parses the file. Unchanged files
    remain byte-identical. This pass never reads a private directory or PDF.
    """
    changed, total = [], 0
    for name, data in list(files.items()):
        suffix = PurePosixPath(name).suffix.lower()
        if suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if suffix == '.json':
            value = json.loads(text)
            masked, count = _mask_json(value)
            if count:
                text = json.dumps(masked, ensure_ascii=False, separators=(',', ':')) + '\n'
        else:
            text, count = mask_text(text)
        if count:
            files[name] = text.encode('utf-8')
            changed.append(name)
            total += count
    return {'files_masked': len(changed), 'identifiers_masked': total, 'paths': sorted(changed)}
