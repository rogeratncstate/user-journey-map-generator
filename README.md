# User Journey Map Generator

This repository hosts a static web experience that visualizes learner journey maps from
JSON files stored in GitHub. The front-end dynamically enumerates every course folder
under `data/` and renders each persona file.

The project now includes automation to generate new personas with ChatGPT and commit
them directly to your GitHub repository.

## Prerequisites

* Python 3.9+
* An OpenAI API key with access to GPT-4o or a compatible model
* A GitHub personal access token (classic or fine-grained) with permission to write to
  this repository

Install the Python dependency:

```bash
pip install -r requirements.txt
```

## Configure environment variables

Copy `.env.example` to `.env` (or export the variables in your shell) and fill in the
values:

* `OPENAI_API_KEY` – OpenAI credential used to call the Chat Completions API
* `GITHUB_REPO` – target repository in the form `owner/repo`
* `GITHUB_TOKEN` – GitHub token capable of creating and updating files via the Contents API
* `GITHUB_BRANCH` – optional branch name (defaults to `main`)

You can use tools like [`direnv`](https://direnv.net/) or `python-dotenv` to load the
variables automatically when running the script.

## Prepare course documents

Place the feasibility assessment, course design plan, Lightcast summary, and any other
market research in `docs/<Course_Folder>/`. Supported file types are `.md`, `.txt`, and
`.json`. Convert PDF and slide decks to text before running the generator.

```
docs/
└── Introduction_to_Data_Science/
    ├── feasibility_assessment.md
    ├── course_design_notes.md
    └── lightcast_industry_summary.txt
```

## Generate personas and upload them to GitHub

Run the generator once the course collateral is in place. The example below produces
three personas for `Introduction_to_Data_Science`, saves the JSON locally in the
`generated/` folder, and pushes the files to `data/Introduction_to_Data_Science/` in the
configured GitHub repository.

```bash
python tools/generate_personas.py Introduction_to_Data_Science
```

Useful flags:

* `--personas` – number of personas to request (default: 3)
* `--model` – change the OpenAI model (default: `gpt-4o`)
* `--dry-run` – skip the GitHub upload and only write local JSON files
* `--update-manifest` – refresh `data/manifest.json` using the remote GitHub directory
* `--manifest-only` – skip OpenAI generation and only refresh the manifest

Example dry run:

```bash
python tools/generate_personas.py Introduction_to_Data_Science --dry-run --personas 4
```

During a non-dry run the script will:

1. Call OpenAI with the concatenated course documents.
2. Validate the returned JSON against the journey map schema.
3. Create or update `data/<Course_Folder>/<persona>.json` in GitHub.
4. Optionally regenerate the offline `data/manifest.json` fallback using the remote
   directory listing.

Generated files are also stored locally under `generated/` for auditing and version
control if desired.

## Local fallback manifest

When the web app cannot reach GitHub it uses `data/manifest.json` to locate personas. To
keep this fallback up to date, run the generator with `--update-manifest` or execute the
following standalone command after adding personas directly in GitHub:

```bash
python tools/generate_personas.py --manifest-only --update-manifest
```

The `--manifest-only` flag only requires valid GitHub credentials and bypasses the
OpenAI request entirely.

## Troubleshooting

* **401 Unauthorized from GitHub** – confirm `GITHUB_TOKEN` is valid and has the `repo`
  scope.
* **OpenAI JSON parsing errors** – rerun the command; if the model keeps returning
  invalid JSON, tighten the prompt or reduce `--temperature`.
* **Large document sets** – consider summarizing long PDFs before feeding them to the
  model to avoid token limits.

## Run the automated smoke-test bot

After adding personas you can verify the front-end renders them correctly by running
the Playwright bot in `tools/test_app_bot.py`. The bot boots a local `http.server`,
loads the app, selects the first course and persona, and asserts that key sections are
populated without console errors.

```bash
pip install -r requirements.txt
python tools/test_app_bot.py
```

The bot automatically bootstraps Playwright before it runs. On Linux this includes
calling ``python -m playwright install --with-deps chromium`` so the required system
libraries are available. If your environment already manages Playwright, pass
``--skip-bootstrap`` (or set ``PLAYWRIGHT_SKIP_BOOTSTRAP=1``) to bypass the helper.

To target a deployed build instead of the local static server, pass a full URL:

```bash
python tools/test_app_bot.py --base-url https://your-site.example/index.html
```

Use `--no-headless` to watch the interactions in a visible browser window. If you
want to pre-install the dependencies in CI or another automated environment, run:

```bash
python tools/bootstrap_playwright.py
```

You can then invoke the bot with `--skip-bootstrap` to avoid redundant work. For
more advanced scenarios (custom browsers, dry runs, different sentinel locations)
see `python tools/bootstrap_playwright.py --help`. Additional troubleshooting tips
are available in the [Playwright documentation](https://playwright.dev/python/docs/troubleshooting#installing-browsers).

Contributions and enhancements are welcome!
