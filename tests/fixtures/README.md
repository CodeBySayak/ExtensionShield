# Golden Snapshot Test Fixtures

This directory contains representative scan output fixtures used for golden snapshot testing.

## Purpose

These fixtures serve as baseline snapshots to ensure that refactors don't silently change:
- **Scores** (must stay in [0, 100])
- **Verdicts** (BLOCK/ALLOW/NEEDS_REVIEW)
- **Top 3 evidence items** (must remain stable)

## Fixture Files

Currently contains 5 representative scan outputs:
- `abikfbojmghmfjdjlbagiamkinbmbaic_results.json` - Equalizer extension (BLOCK verdict, score 85)
- `edacconmaakjimmfgnblocblbcdcpbko_results.json` - Session Buddy extension (NEEDS_REVIEW, score 92)
- `jnkmfdileelhofjcijamephohjechhna_results.json` - Google Analytics Debugger (BLOCK, score 80)
- `nkabooldphfdjcbhcodblkfmigmpchhi_results.json` - Pinterest extension (NEEDS_REVIEW, score 86)
- `nobaaibkcalggmjnjhnlmmcldllpogjp_results.json` - Tab Slider (NEEDS_REVIEW, score 90)

## Adding More Fixtures

To add more fixtures (target: 20-30 total):

1. Copy a scan result JSON file to this directory with the naming pattern: `{extension_id}_results.json`
2. Run `python3 tests/generate_snapshots.py` to regenerate golden snapshots
3. Update `GOLDEN_SNAPSHOTS` in `tests/test_golden_snapshots.py` with the new values
4. Run `uv run pytest tests/test_golden_snapshots.py -v` to verify

## Updating Golden Snapshots

When making intentional changes to scoring or verdict logic:

1. Update the code
2. Run `python3 tests/generate_snapshots.py` to see new values
3. Update `GOLDEN_SNAPSHOTS` in `tests/test_golden_snapshots.py`
4. Run tests to verify: `uv run pytest tests/test_golden_snapshots.py -v`

## Test Coverage

The golden snapshot tests validate:
- ✅ Score is in valid range [0, 100]
- ✅ Verdict matches golden snapshot
- ✅ Score matches golden snapshot  
- ✅ Top 3 evidence items match golden snapshot

If a test fails, it means either:
1. A bug was introduced (fix it)
2. An intentional change was made (update the snapshot)

