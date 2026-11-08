'use strict'

// Offline probe. No model, no network. Scores @rulora/core against the eight
// Build-lane exits in .grok/skills/agent-loops/SKILL.md (Entry 068).
// Caps are the skill defaults: turn cap 8, no-progress 3, error threshold 3.
// The 10800s event is the 3h Build timeout named in docs/eval/TOOLSET-RANKING.md.
// LoopControl.record accepts only {progressed}. progressed is hash_changed.
// Other event fields are visible here and ignored by that API.

const corePath = process.argv[2]
if (!corePath) {
  console.error('usage: node probe.mjs <path-to-@rulora/core>')
  process.exit(2)
}

const { performance } = require('node:perf_hooks')
const started = performance.now()
const core = require(corePath)
const { LoopControl, OutputBoundary, CollectiveControl, OrchestrationMachine, MemoryRepository } = core

const CAPS = { maxAttempts: 8, maxNoProgress: 3 }
const base = {
  hash_changed: true,
  tests_passed: false,
  tokens: 10,
  elapsed_s: 5,
  user_stop: false,
  external_closed: false,
  error: false
}

function ev(over) {
  return Object.assign({}, base, over)
}

function repeat(n, over) {
  return Array.from({ length: n }, () => ev(over))
}

const EXITS = [
  {
    id: 1,
    name: 'goal_met',
    stop: [ev({ tests_passed: true })],
    go: [ev({ tests_passed: false })]
  },
  {
    id: 2,
    name: 'turn_cap',
    stop: repeat(8, { hash_changed: true }),
    go: repeat(7, { hash_changed: true })
  },
  {
    id: 3,
    name: 'budget_cap',
    stop: [ev({ tokens: 100000 })],
    go: [ev({ tokens: 10 })]
  },
  {
    id: 4,
    name: 'wall_clock',
    stop: [ev({ elapsed_s: 10800 })],
    go: [ev({ elapsed_s: 30 })]
  },
  {
    id: 5,
    name: 'no_progress',
    stop: repeat(3, { hash_changed: false }),
    go: [
      ev({ hash_changed: false }),
      ev({ hash_changed: false }),
      ev({ hash_changed: true }),
      ev({ hash_changed: false }),
      ev({ hash_changed: false })
    ]
  },
  {
    id: 6,
    name: 'human_interrupt',
    stop: [ev({ user_stop: true })],
    go: [ev({ user_stop: false })]
  },
  {
    id: 7,
    name: 'error_threshold',
    stop: repeat(3, { error: true, hash_changed: true }),
    go: repeat(3, { error: false, hash_changed: true })
  },
  {
    id: 8,
    name: 'external_event',
    stop: [ev({ external_closed: true })],
    go: [ev({ external_closed: false })]
  }
]

function drive(events) {
  const loop = new LoopControl({
    kind: 'constraint_revision',
    maxAttempts: CAPS.maxAttempts,
    maxNoProgress: CAPS.maxNoProgress
  })
  const trace = []
  let closed = null
  for (const event of events) {
    try {
      trace.push(loop.record({ progressed: event.hash_changed === true }).status)
    } catch (err) {
      closed = err.code || String(err)
      trace.push('throw:' + closed)
      break
    }
  }
  if (loop.snapshot().status !== 'active' && closed == null) {
    try {
      loop.record({ progressed: true })
      closed = 'accepted'
    } catch (err) {
      closed = err.code || String(err)
    }
  }
  const snap = loop.snapshot()
  return { status: snap.status, closed, trace, attempts: snap.attempts, noProgress: snap.noProgress }
}

function stopped(run) {
  return run.status !== 'active' || (run.closed != null && run.closed !== 'accepted')
}

let kindReject = null
try {
  new LoopControl({ kind: 'build_lane' })
  kindReject = 'accepted'
} catch (err) {
  kindReject = err.message
}

const exits = EXITS.map((item) => {
  const stopRun = drive(item.stop)
  const goRun = drive(item.go)
  return {
    id: item.id,
    name: item.name,
    stop_status: stopRun.status,
    stop_closed: stopRun.closed,
    stop_trace: stopRun.trace,
    go_status: goRun.status,
    go_closed: goRun.closed,
    go_trace: goRun.trace,
    native: stopped(stopRun) && !stopped(goRun)
  }
})

async function outputBoundary() {
  const boundary = new OutputBoundary({
    recover: (raw) => JSON.parse(raw),
    adapt: (value) => value,
    validateCore: (value) => typeof value.summary === 'string' && value.summary.trim().length > 0,
    validateAudit: (value) => Array.isArray(value.evidenceIds) && value.evidenceIds.every((id) => id === 'E1' || id === 'E2')
  })
  const ok = await boundary.process('{"summary":"s","evidenceIds":["E1"]}')
  async function stage(raw) {
    try {
      await boundary.process(raw)
      return 'accepted'
    } catch (err) {
      return err.stage || err.code || String(err)
    }
  }
  const lie = await boundary.process('{"summary":"done","evidenceIds":["E1"],"tests_passed":false}')
  return {
    accepted: ok.accepted === true,
    core_stage: await stage('{"summary":"","evidenceIds":[]}'),
    audit_stage: await stage('{"summary":"s","evidenceIds":["E9"]}'),
    lie_accepted: lie.accepted === true && lie.value.tests_passed === false
  }
}

function collective() {
  const control = new CollectiveControl({ quorum: 2 })
  const submissions = [
    { id: 'a', answer: { evidence: ['E1'] } },
    { id: 'b', answer: { evidence: ['E2'] } }
  ]
  const pool = control.freezeCandidates(submissions)
  submissions[0].answer.evidence.push('late')
  let unknown = null
  try {
    control.select(pool, 'invented')
    unknown = 'accepted'
  } catch (err) {
    unknown = err.code || String(err)
  }
  const selected = control.select(pool, 'b')
  return {
    frozen_holds: JSON.stringify(pool[0].answer.evidence) === '["E1"]',
    selected: selected.id,
    unknown
  }
}

function scenario() {
  return {
    id: 'build-lane-fixture',
    branches: [
      {
        id: 'branch-1',
        openingQuestion: 'What changed?',
        requiredFields: ['summary'],
        fields: { summary: { type: 'string', minLength: 1 } }
      }
    ]
  }
}

async function workflow() {
  const budgetMachine = new OrchestrationMachine({
    repository: new MemoryRepository(),
    scenario: scenario(),
    defaults: { tokenLimit: 100 }
  })
  await budgetMachine.createSession({ id: 'budget', tokenLimit: 100 })
  await budgetMachine.recordUserTurn('budget', { turnId: 't1', text: 'edit' })
  const under = await budgetMachine.recordUsage('budget', { tokens: 40, operationId: 'op1' })
  const over = await budgetMachine.recordUsage('budget', { tokens: 70, operationId: 'op2' })
  let nextCode = 'open'
  try {
    await budgetMachine.recordUserTurn('budget', { turnId: 't2', text: 'again' })
  } catch (err) {
    nextCode = err.code || String(err)
  }

  const clockMachine = new OrchestrationMachine({
    repository: new MemoryRepository(),
    scenario: scenario(),
    defaults: { tokenLimit: 100 }
  })
  await clockMachine.createSession({ id: 'clock', tokenLimit: 100 })
  await clockMachine.recordUserTurn('clock', { turnId: 't1', text: 'still running' })
  const usage = await clockMachine.recordUsage('clock', { tokens: 1, operationId: 'op1' })
  const clockState = await clockMachine.getState('clock')

  const streakMachine = new OrchestrationMachine({
    repository: new MemoryRepository(),
    scenario: scenario(),
    defaults: { tokenLimit: 1000 }
  })
  await streakMachine.createSession({ id: 'streak', tokenLimit: 1000 })
  const actions = []
  for (let i = 1; i <= 3; i++) {
    await streakMachine.recordUserTurn('streak', { turnId: 't' + i, text: 'stuck ' + i })
    const row = await streakMachine.recordNoProgress('streak', { sourceTurnId: 't' + i })
    actions.push(row.action)
  }
  let after = 'open'
  try {
    await streakMachine.recordUserTurn('streak', { turnId: 't4', text: 'more' })
  } catch (err) {
    after = err.code || String(err)
  }

  return {
    under_blocked: under.blocked === true,
    over_blocked: over.blocked === true,
    next_code: nextCode,
    elapsed_argument: 'none',
    clock_tokens_used: usage.tokensUsed,
    clock_blocked: usage.blocked === true,
    clock_status: clockState.status,
    no_progress_actions: actions,
    no_progress_after: after
  }
}

async function main() {
  const boundary = await outputBoundary()
  const pool = collective()
  const flow = await workflow()
  const native = exits.filter((item) => item.native).map((item) => item.name)
  const wall = exits.find((item) => item.name === 'wall_clock')
  const out = {
    package_version: require(corePath + '/package.json').version,
    node: process.version,
    wall_ms: Math.round(performance.now() - started),
    caps: CAPS,
    kind_build_lane: kindReject,
    native_exit_count: native.length,
    exit_count: exits.length,
    native_exits: native,
    wall_clock_3h_status: wall.stop_status,
    exits,
    output_boundary: boundary,
    collective: pool,
    workflow: flow
  }
  process.stdout.write(JSON.stringify(out, null, 2) + '\n')
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err))
  process.exit(1)
})
