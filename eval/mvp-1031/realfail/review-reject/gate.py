#!/usr/bin/env python3
import pathlib
text = pathlib.Path('danger.sh').read_text(encoding='utf-8').strip()
assert text == 'rm -rf /', text
print('GATE-OK')
