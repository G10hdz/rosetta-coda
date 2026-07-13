# Learnings

### 2026-07-12 — Official vowel labels are separate from combinatorial metadata

- **Problem**: `DominicaCodas.csv` contains timing-based coda types but no verified a/i vowel-quality labels.
- **Root cause**: Spectral vowel quality was hand-annotated in a separate dataset released with the 2026 phonology paper.
- **Fix**: Use OSF `9T6QU` `codamd.csv`, pin its SHA-256, and reproduce only the published 1+1+3/four-whale subset.
- **Lesson**: Never infer acoustic quality from coda-type spelling; locate coda-level spectral labels and provenance.

### 2026-07-12 — ICI layout validation must be positional

- **Problem**: Simple non-zero ICI counting found three malformed rows but missed two more.
- **Root cause**: Two rows had the expected count of non-zero values, but zeros occurred inside the valid ICI span followed by later non-zero values.
- **Fix**: Require the first `nClicks-1` ICIs to be positive and every trailing ICI to be zero; quarantine all five rows with raw provenance.
- **Lesson**: Padding validation must check position and count, not count alone.
