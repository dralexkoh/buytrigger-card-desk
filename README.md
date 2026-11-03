# BuyTrigger.Cards — Card Desk by Alex & Oscar

V1.1 · Daily Raw refresh infrastructure · 3 November 2026. Free card news, collecting guides, TCG Modern Index and Top 50 Raw editions.

Website: https://dralexkoh.github.io/buytrigger-card-desk/

This repository contains the public static website only. Personal holdings, costs, photographs, owner analytics and authentication data are excluded.

## Current scope

- Ten source-linked illustrated articles, six short news updates, direct story pages and RSS.
- 100 exact English issues and actual catalogue artwork: 96 from TCGdex and four from Limitless, with per-image provenance.
- Daily TCGplayer Raw guides via TCGCSV from 1 January through 2 November 2026. Current references: 99 USD guides and one separate EUR reference; currencies are not mixed. Missing observations remain null. The isolated Mew Blue $5 observation on 7 October is preserved in the source data but excluded from charts and returns with a visible receipt.
- Fixed retrospective USD cohorts: 82 complete-history issues and 99 current priced issues, (the latest 99 have only one common date, so no return), with distinct frozen IDs, equal starting weights and no silent component removal. No private legacy index is imported.
- PSA 9/10, population and transaction-level data remain pending. The daily refresh workflow is configured; the first successful scheduled check is pending. The visible source date, check time and update receipt show what actually ran.
- Top 50: 50 English exact printings ranked by positive Raw USD market guide on 2 November 2026, older cards included. All 45,649 category-3 source rows screened; no unresolved eligible higher-priced rows. Unpriced issues remain unranked; this is not a world-value or liquidity leaderboard.
- Top 50 real pictures: 32 matching-printing scans and 18 clearly captioned reference scans. No altered stamps or generated card art. 46 TCGdex, three Limitless and one Catch’em/TCGplayer catalogue source.
- Top 50 history: 330 source dates, 8 February 2024 through 2 November 2026. First archive plus calendar month ends in 2024–25; daily in 2026. January 2024 is unavailable. 13,208 usable guide observations; 113 suspected observations held with originals preserved. The fixed long-history comparison uses 14 complete-history printings; all 50 have only one common priced date and no full-50 return. Both current selection and completeness filtering create hindsight bias.
- Three independently source-linked historic Heritage auction highlights, separate from the Raw ranking and charts. No current-record claim.
- Three-outcome grading calculator, all 50 gallery/table views, exact-printing search, individual history/evidence tabs and three-outcome bars.
- No membership, active ads, affiliate programme or visitor tracking in this release. Custom Cards traffic reporting is prepared separately for the existing private CRM; the collector remains disabled until deployment and verification. Revenue integrations and the custom domain follow separately.

## Credits and reuse

Original brand illustrations and editorial graphics belong to this project. Card and product names identify the subject of independent research and do not imply endorsement. Original Pokémon press assets are included only in the free editorial edition under the press-site media guidelines. They remain their respective rights holders’ property; no blanket reuse licence is granted. Reassess the press-asset scope before monetization.

TCGdex database licensing and exact image provenance are included in `assets/TCGDEX-LICENSE.txt` and `image-sources.json`; underlying Pokémon artwork remains its owners’ property. Modern daily archive hashes are in `market-sources.json`; Top 50 selection, archive dates, holds and hashes are in `top50-sources.json`. Top 50 image provenance and visible printing limits are in `top50-image-sources.json`. The Catch’em thumbnail is a distinct catalogue source, not covered by TCGdex database licensing.

Sources: https://tcgcsv.com/faq and https://press.pokemon.com/en/Assets-Use-Terms . Exact article references appear on each story. Copyright and other rights are reserved where applicable.

## Corrections

Use this repository’s Issues page for public editorial corrections. Do not submit personal or collection information.

## Daily Raw maintenance

GitHub Actions checks the source build at 21:17, 23:17 and 07:17 UTC. A repeated build requires only the source marker request. New validated observations extend the existing histories and retain their receipts. A missing quote or unusual daily move keeps the prior dated quote and leaves a chart gap for review. A source failure preserves the last accepted data and publishes a failure notice when validation succeeds.

The fixed November selection is repriced; the updater does not re-rank the whole market or silently change basket membership. The single EUR reference is dated separately and is not refreshed by this USD feed. PSA data remains pending. Schedule execution may be delayed by GitHub; the status band distinguishes configuration from a successful automatic run.

To validate and build the public artifact:

```sh
python3 -m pip install -r requirements.txt
npm test
npm run typecheck
npm run build
npm run check:artifact
```

To run one isolated collection and validation pass, supply output paths outside this repository:

```sh
python3 scripts/run_daily_pipeline.py --dist-out /tmp/buytrigger-public --receipt /tmp/buytrigger-refresh.json --cache-dir /tmp/buytrigger-feed-cache --run-kind manual
```

Only `dist/` is published. Build sources, tests and operational refresh state remain outside the Pages artifact. The frozen test fixture contains already-public price payloads. The workflow commits only validated price/history/status paths, checks the remote head before saving and verifies deployed file hashes.
