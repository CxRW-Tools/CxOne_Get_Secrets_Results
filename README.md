# CxOne Secrets Results

A tool that collects **secrets scan results** from all projects in your Checkmarx One tenant and outputs a single CSV.

## Overview

This tool:

1. **Discovers all projects** in your CxOne tenant (`GET /api/projects`).
2. **Finds the latest secrets scan per project** — For each project, the most recent **Completed** scan that has secrets enabled (microengines config with `2ms: "true"`) is selected via `GET /api/scans`.
3. **Collects secrets results** — For each selected scan, fetches all results from `GET /api/results?scan-id=...` (paginated) and keeps only findings with type `sscs-secret-detection`.
4. **Writes one CSV** — Single file with one row per secret: **projectId, projectName, scanId, id, firstFoundAt, foundAt, ruleName, fileName, line** (ruleName, fileName, line come from each result’s `data`).

## Features

- Multi-threaded execution for project discovery, scan finding, and results collection
- Progress tracking with live status updates
- Robust error handling with detailed logging and an exception report
- Configurable via environment variables or command-line arguments
- Retry logic and rate-limit handling for API calls

## Project Structure

```
.
├── src/
│   ├── models/
│   │   ├── project.py
│   │   └── scan.py
│   ├── utils/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── api_client.py
│   │   ├── progress.py
│   │   ├── file_manager.py
│   │   ├── debug_logger.py
│   │   └── exception_reporter.py
│   └── operations/
│       ├── base.py
│       ├── project_discovery.py
│       ├── secrets_scan_finder.py
│       └── secrets_results_collector.py
├── main.py
├── requirements.txt
├── example.env
├── LICENSE
└── README.md
```

## Setup

1. Clone this repository.
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copy `example.env` to `.env` and set your CxOne credentials:

   ```powershell
   copy example.env .env
   # Edit .env with your credentials
   ```

## Configuration

### Environment Variables

Use a `.env` file or set:

- `CXONE_BASE_URL` — Region base URL (e.g. `https://ast.checkmarx.net`)
- `CXONE_TENANT` — Tenant name
- `CXONE_API_KEY` — API key for authentication
- `CXONE_DEBUG` — Set to `true` to enable debug output (optional)
- `CXONE_MAX_WORKERS` — Max worker threads for results collection (optional, default 10)
- `CXONE_OUTPUT_DIR` — Output directory (optional, default `./output`)

You can use different env files per tenant (e.g. `.env-prod`, `.env-test`) and pass them with `--env-file`.

### Command Line Arguments

- `--env-file` — Path to environment file (default: `.env`)
- `--base-url` — Region base URL
- `--tenant-name` — Tenant name
- `--api-key` — API key for authentication
- `--debug` — Enable debug output
- `--max-workers` — Max worker threads for results collection
- `--output-dir` — Output directory for the CSV

Command line arguments override environment variables.

## Usage

### Basic

```powershell
python main.py
```

### With options

```powershell
python main.py --env-file .env-prod
python main.py --debug --output-dir "C:\Reports"
python main.py --base-url "https://ast.checkmarx.net" --tenant-name "myorg" --api-key "YOUR_API_KEY"
python main.py --output-dir ./out --max-workers 10
```

## Output

The tool writes files under the output directory (default `./output`):

### 1. Data file (CSV)

**Filename:** `secrets_results_{tenant}_{timestamp}.csv`

Columns:

| Column       | Description                                      |
|-------------|---------------------------------------------------|
| projectId   | Project ID                                       |
| projectName | Project name                                     |
| scanId      | Scan ID used for results                          |
| id          | Result ID                                        |
| firstFoundAt| When the secret was first found                   |
| foundAt     | When the secret was found in this scan            |
| ruleName    | Secret rule name (e.g. Authenticated-Url)         |
| fileName    | File path                                        |
| line        | Line number                                      |

### 2. Exception report (TXT)

**Filename:** `secrets_results_{tenant}_{timestamp}_report.txt`

Contains summary statistics (projects, scans found, secrets count, execution time) and any errors (projects without a secrets scan, scan errors, results fetch errors, API errors).

### 3. Debug log (TXT)

**Filename:** `secrets_results_{tenant}_{timestamp}_debug.txt`

Timestamped log of operations. Always generated; use `--debug` to also print to the console. Useful for long runs:

```powershell
Get-Content -Path "output\secrets_results_mytenant_20260219_120000_debug.txt" -Wait -Tail 50
```

## Scan selection (secrets scan)

A scan is used for secrets only if:

- In **statusDetails** there is an entry with `name: "microengines"` and `status: "Completed"` (the microengines engine completed successfully), and  
- In **metadata.configs** there is an entry with `type: "microengines"` and that entry’s `value` has `"2ms": "true"`.

The tool requests scans with `project-id`, `statuses=Completed,Partial`, and `sort=-created_at`, then picks the first scan in that order that satisfies the above.

## Performance and errors

- **Threading:** Project discovery is single-threaded; scan finding and results collection use configurable worker pools (see `max_workers_scans` / `max_workers_results` in config and `--max-workers` for results).
- **API:** Requests use retries with backoff; 429 responses trigger a longer wait.
- **Partial results:** If some projects or scans fail, the run continues and the CSV and report reflect what succeeded; the report lists failures.

## Troubleshooting

- **Authentication errors:** Check base URL, tenant name, and API key (and that the key is valid and not expired).
- **No projects:** Confirm the tenant has projects and the API key has access.
- **No secrets scans:** Ensure at least one Completed scan per project has microengines enabled with `2ms: "true"` in its config.
- **No or few results:** Confirm those scans actually produced `sscs-secret-detection` results in the Checkmarx One UI or API.
- **Rate limiting or timeouts:** Lower `--max-workers` or increase timeouts in config if needed.

## License

MIT License

Copyright (c) 2024-2025

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the conditions that the above copyright notice and this permission notice be included in all copies or substantial portions of the Software. The software is provided "AS IS", without warranty of any kind.
