#!/usr/bin/env python3
import os, sys
path = os.environ['PFY_PROMPT_LOG']
with open(path, 'a', encoding='utf-8') as handle:
    handle.write('\n'.join(sys.argv) + '\n---PROMPT---\n')
grok = os.environ['PFY_REAL_GROK']
os.execv(grok, [grok, *sys.argv[1:]])
