**Project Overview**

Simple Python scraper that searches python.org for a library name using Selenium and saves results.

**Prerequisites**

- Python 3.8+
- Google Chrome installed (chromedriver managed automatically)

**Install dependencies**

```bash
python -m pip install --upgrade pip
python -m pip install selenium webdriver-manager
```

**Files**

- `scrapper.py`: main script to run searches and save snapshots/results.
- `search_results.csv`: optional CSV file where appended search rows are stored.

**Usage**

- Interactive prompt:

```bash
python scrapper.py
# then type the library name when prompted
```

- Provide the library name on the command line and save a JSON snapshot named after the query:

```bash
python scrapper.py pillow --save-json
```

- Append results to CSV (defaults to `search_results.csv`) and also save JSON snapshot:

```bash
python scrapper.py pillow --save-json --save-csv
```

- Use a custom CSV filename:

```bash
python scrapper.py pillow --save-csv my_searches.csv
```

**What `--save-json` writes**

It saves a JSON file named `<sanitized_query>.json` containing:
- `url`: page URL used
- `title`: page title
- `query`: the search query
- `timestamp`: UTC ISO timestamp
- `html`: full rendered HTML (page source)

**What CSV contains**

Each appended row contains `timestamp`, `query`, `page_url`, `page_title`, `results_json` (stringified JSON array), and `json_snapshot` (filename written, if any).

**Notes & Troubleshooting**

- If you see `ModuleNotFoundError: No module named 'webdriver_manager'`, install `webdriver-manager` as shown above.
- If Selenium reports `ElementClickInterceptedException`, the script uses Enter key submission and removes the `fundraiser-banner-host` overlay when necessary.

**Next improvements (optional)**

- Add `--save-json-path` to specify an arbitrary path/filename.
- Add unit tests and a `requirements.txt` for pinned deps.

**License**

MIT-style — see project `LICENSE` file.
# webscraper01
This website scrape data from websites using python.
