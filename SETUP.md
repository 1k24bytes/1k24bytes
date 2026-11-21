# Three Worlds profile README — setup

This is the implementation kit for `1k24bytes/1k24bytes`. It does not change your GitHub repository automatically.

## 1. Add the files

1. Download and extract `profile-readme-kit.zip`.
2. Open your GitHub repository: https://github.com/1k24bytes/1k24bytes
3. Upload the folders and files from this kit into the repository root. Keep the folder structure exactly as supplied.
4. Replace the repository's existing `README.md` with the `README.md` from this kit. Keep `ascii-banner.svg`, `terminal.svg`, and your existing PNG if you may want them later; this kit does not require deleting them.
5. Commit the upload to the `main` branch.

## 2. Run the first refresh

1. Open the repository's **Actions** tab.
2. Select **Update profile README cards**.
3. Click **Run workflow** and run it on `main`.
4. Wait for the workflow to finish. It fetches the public contribution calendar, calculates monthly totals/streaks/active days/busiest day, regenerates the SVGs, and commits changed cards.
5. Refresh `https://github.com/1k24bytes` to see the new profile README.

The workflow is scheduled for 08:00 India Standard Time every day. The repository needs Actions enabled and the workflow's `GITHUB_TOKEN` must have permission to write contents. The workflow declares `permissions: contents: write`.

## 3. Preview locally

From the extracted folder:

```bash
python -m pip install -r requirements.txt
STATIC=1 python scripts/render_readme_cards.py
```

`STATIC=1` disables entrance and shimmer animations so you can inspect final frames. Normal rendering leaves the animations enabled:

```bash
python scripts/render_readme_cards.py
```

Open `preview.html` in a browser. If cards show blank in your viewer, build and open the standalone version (all SVGs inlined, no external files):

```bash
python scripts/build_preview.py
```

To fetch fresh GitHub data locally before rendering:

```bash
python scripts/fetch_contributions.py --username 1k24bytes
python scripts/render_readme_cards.py
```

## 4. Portrait

The hero currently includes a clearly marked ASCII portrait placeholder because no personal photo was supplied with this request. Send a front-facing photo you are comfortable making public, and the portrait can be converted into a real ASCII treatment and inserted into `hero.svg` by the generator.

## Notes

- The README embeds local SVGs with `<img>` links. It does not embed the HTML preview, JavaScript, or external CSS.
- Instrument Serif and Geist are fetched from Google Fonts and subsetted to WOFF data in the generated SVGs during a network-enabled render. Font files are not stored in this kit.
- The contribution fetcher reads the same public GitHub contribution calendar shown on your profile. It intentionally fails rather than inventing exact daily counts if GitHub changes its markup.
- GitHub profile contribution totals can include private activity depending on the account's contribution-graph settings. The public page is the source used by this workflow.
- You can edit project descriptions and links in `scripts/render_readme_cards.py`.
