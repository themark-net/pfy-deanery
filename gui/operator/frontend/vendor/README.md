# Cytoscape.js 3.35.0 (vendored dist)

One minified file for the operator Runs graph (`gui/operator/frontend/lane-graph.js`). Design: `docs/design/LANE-GRAPH-IA.md`.

| | |
|---|---|
| Upstream | https://github.com/cytoscape/cytoscape.js |
| Pin | 3.35.0 |
| File | `cytoscape.min.js` |
| sha256 | `71fa9ebec21a7ca2c40cff6aacc30d1f6464e363662ad4b2c197e1adc770cd94` |
| License | MIT, upstream text in `LICENSE` |
| Bytes | 442752 |

Not a git subtree. ADR-0003 and `SUBTREES.md` keep whole tool repos out of this tree unless every I4 embed rule is met. Cytoscape is a GUI library we do not fork. The operator window has no bundler, so the Runs view needs this single offline build. The pin is the dist file only, not the project history.
