#!/usr/bin/env python3
from pathlib import Path
kept = Path('kept.py').read_text(encoding='utf-8')
if kept != 'value = 1\n':
    raise SystemExit('kept %r' % kept)
print('GATE-OK')
