// Offline probe of @kanbots/dispatcher worktree helpers.
// Reads the pinned checkout. Does not spawn an agent CLI and does not open Electron.
import { execFile } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const gitEnv = {
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  TMPDIR: process.env.TMPDIR,
  LANG: process.env.LANG || 'C.UTF-8',
  GIT_CONFIG_GLOBAL: '/dev/null',
  GIT_CONFIG_NOSYSTEM: '1',
  GIT_TERMINAL_PROMPT: '0',
};

function git(cwd, args) {
  return execFileAsync('git', args, { cwd, env: gitEnv, encoding: 'utf8' });
}

async function gitResult(cwd, args) {
  try {
    const out = await git(cwd, args);
    return { code: 0, stdout: out.stdout, stderr: out.stderr };
  } catch (err) {
    return {
      code: typeof err.code === 'number' ? err.code : 1,
      stdout: err.stdout || '',
      stderr: err.stderr || String(err.message || err),
    };
  }
}

function arg(name) {
  const i = process.argv.indexOf(name);
  if (i < 0 || !process.argv[i + 1]) {
    throw new Error(`missing ${name}`);
  }
  return process.argv[i + 1];
}

const src = arg('--src');
const repo = arg('--repo');
const remote = arg('--remote');

const dispatcher = join(src, 'packages/dispatcher/src');
const worktreeMod = await import(pathToFileURL(join(dispatcher, 'worktree.ts')).href);
const identityMod = await import(pathToFileURL(join(dispatcher, 'worktree-identity.ts')).href);
const containMod = await import(pathToFileURL(join(dispatcher, 'containment.ts')).href);
const checksMod = await import(pathToFileURL(join(dispatcher, 'checks.ts')).href);

const issueNumber = 78;
const runId = 1;
const branch = worktreeMod.defaultBranchName({ issueNumber, runId });
const worktreePath = worktreeMod.defaultWorktreePath({ repoPath: repo, issueNumber, runId });

await mkdir(dirname(worktreePath), { recursive: true });

const t0 = performance.now();
const created = await worktreeMod.createWorktree({
  repoPath: repo,
  branch,
  worktreePath,
  baseRef: 'HEAD',
});
const createMs = performance.now() - t0;

const hookPath = (await git(worktreePath, ['rev-parse', '--git-path', 'hooks'])).stdout.trim();
const prePush = join(
  hookPath.startsWith('/') ? hookPath : join(worktreePath, hookPath),
  'pre-push',
);
let prePushText = '';
try {
  prePushText = await readFile(prePush, 'utf8');
} catch {
  prePushText = '';
}

const explicit = `refs/heads/${branch}:refs/heads/${branch}`;
const headSpec = `HEAD:refs/heads/${branch}`;
const pushExplicitBefore = await gitResult(worktreePath, ['push', remote, explicit]);
const pushHeadBefore = await gitResult(worktreePath, ['push', remote, headSpec]);
await gitResult(remote, ['update-ref', '-d', `refs/heads/${branch}`]);

const t1 = performance.now();
const stamped = await identityMod.stampWorktreeIdentity({
  worktreePath,
  runId,
  issueNumber,
});
const stampMs = performance.now() - t1;

const hooksPath = await gitResult(worktreePath, ['config', '--worktree', '--get', 'core.hooksPath']);
const pushExplicitAfter = await gitResult(worktreePath, ['push', remote, explicit]);

await writeFile(join(worktreePath, 'GAP.md'), 'probe note\n', { flag: 'a' });
const add = await gitResult(worktreePath, ['add', 'GAP.md']);
const commit = await gitResult(worktreePath, ['commit', '-m', 'lane note']);
const message = (await gitResult(worktreePath, ['log', '-1', '--format=%B'])).stdout;
const author = (await gitResult(worktreePath, ['log', '-1', '--format=%an <%ae>'])).stdout.trim();

const outside = '/tmp/kanbots-probe-outside.txt';
const cases = [
  { id: 'write-inside', name: 'Write', input: { file_path: join(worktreePath, 'GAP.md') }, outside: false },
  { id: 'write-abs-outside', name: 'Write', input: { file_path: outside }, outside: true },
  { id: 'edit-parent', name: 'Edit', input: { file_path: '../outside.txt' }, outside: true },
  { id: 'bash-redirect', name: 'Bash', input: { command: `echo x > ${outside}` }, outside: true },
  { id: 'bash-relative', name: 'Bash', input: { command: 'echo x > notes.txt' }, outside: false },
  { id: 'bash-url', name: 'Bash', input: { command: 'curl https://example.com/gap' }, outside: false },
  { id: 'read-outside', name: 'Read', input: { file_path: outside }, outside: true },
];
const containment = cases.map((row) => {
  const result = containMod.inspectToolUse({
    worktreePath,
    name: row.name,
    input: row.input,
  });
  const blocked = result.kind === 'escape';
  return {
    id: row.id,
    name: row.name,
    outside: row.outside,
    kind: result.kind,
    blocked,
    heuristic: result.kind === 'escape' ? result.heuristic : false,
  };
});

const passCheck = await checksMod.runCheck({
  cwd: worktreePath,
  command: { kind: 'tests', command: 'true', args: [] },
  timeoutMs: 2000,
});
const timeoutCheck = await checksMod.runCheck({
  cwd: worktreePath,
  command: { kind: 'tests', command: 'sleep', args: ['5'] },
  timeoutMs: 400,
});

const t2 = performance.now();
await worktreeMod.removeWorktree({ repoPath: repo, worktreePath, force: true });
const removeMs = performance.now() - t2;

const outsideBlocked = containment.filter((row) => row.outside && row.blocked).length;
const outsideTotal = containment.filter((row) => row.outside).length;

const payload = {
  branch: created.branch,
  worktree_path_basename: 'issue-78-1',
  create_ms: round(createMs),
  stamp_ms: round(stampMs),
  remove_ms: round(removeMs),
  create_stamp_remove_ms: round(createMs + stampMs + removeMs),
  hook_installed_by_create: prePushText.includes('cannot be pushed'),
  hook_in_common_dir: prePush.endsWith('.git/hooks/pre-push'),
  pre_push_bytes: prePushText.length,
  stamp: stamped,
  hooks_path_set: hooksPath.code === 0 ? hooksPath.stdout.trim().length > 0 : false,
  push_explicit_before_stamp: summarizePush(pushExplicitBefore),
  push_head_before_stamp: summarizePush(pushHeadBefore),
  push_explicit_after_stamp: summarizePush(pushExplicitAfter),
  commit_code: commit.code,
  commit_add_code: add.code,
  trailer_run: message.includes('Kanbots-Run-Id: 1'),
  trailer_issue: message.includes('Kanbots-Issue: 78'),
  author,
  containment,
  outside_blocked: outsideBlocked,
  outside_total: outsideTotal,
  check_pass: { status: passCheck.status, duration_ms: passCheck.durationMs, summary: passCheck.summary },
  check_timeout: {
    status: timeoutCheck.status,
    duration_ms: timeoutCheck.durationMs,
    summary: timeoutCheck.summary,
  },
};

process.stdout.write(`${JSON.stringify(payload)}\n`);

function round(n) {
  return Math.round(n * 10) / 10;
}

function summarizePush(result) {
  const text = `${result.stderr || ''}\n${result.stdout || ''}`;
  let status = 'other';
  if (text.includes('cannot be pushed')) status = 'rejected by pre-push';
  else if (text.includes('Everything up-to-date')) status = 'up-to-date';
  else if (text.includes('[new branch]')) status = 'new branch';
  else if (text.includes('->')) status = 'updated';
  else if (result.code !== 0) status = 'failed';
  return {
    code: result.code,
    blocked: result.code !== 0 && text.includes('cannot be pushed'),
    status,
  };
}
