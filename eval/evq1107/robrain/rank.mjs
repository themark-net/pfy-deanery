// Rank this lane's corpus with VetoBench vetoRank. Offline only.
// ROBRAIN_VETOBENCH is the packages/vetobench directory of the pinned checkout.
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const root = process.env.ROBRAIN_VETOBENCH
if (!root) {
  console.error('ROBRAIN_VETOBENCH is not set')
  process.exit(2)
}
const { vetoRank } = await import(pathToFileURL(`${root}/dist/adapters.js`).href)
const corpus = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const fixture = JSON.parse(readFileSync(process.argv[3], 'utf8'))
const rows = []
for (const scenario of fixture.scenarios) {
  const rankFiles = vetoRank(scenario, corpus, fixture.as_of)
  const rankNoFiles = vetoRank({ ...scenario, files_in_scope: [] }, corpus, fixture.as_of)
  rows.push({
    id: scenario.id,
    veto: scenario.veto_decision_id,
    trap: scenario.trap,
    rank_files: rankFiles,
    rank_nofiles: rankNoFiles,
  })
}
process.stdout.write(JSON.stringify({ rows }) + '\n')
