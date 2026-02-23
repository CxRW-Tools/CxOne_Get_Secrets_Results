"""Collect secrets results (sscs-secret-detection) for each scan."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from src.operations.base import Operation

SECRETS_TYPE = 'sscs-secret-detection'
CSV_HEADER = ['projectId', 'projectName', 'scanId', 'id', 'firstFoundAt', 'foundAt', 'severity', 'ruleName', 'fileName', 'line']


def _severity_display(raw):
    """Return severity as title case (e.g. HIGH -> High)."""
    if not isinstance(raw, str):
        return str(raw) if raw is not None else ''
    return raw.title()


def _result_to_row(scan, item):
    """Build a CSV row dict from a single result item and scan context."""
    data = item.get('data') or {}
    return {
        'projectId': scan.project_id,
        'projectName': scan.project_name,
        'scanId': scan.scan_id,
        'id': item.get('id', ''),
        'firstFoundAt': item.get('firstFoundAt', ''),
        'foundAt': item.get('foundAt', ''),
        'severity': _severity_display(item.get('severity')),
        'ruleName': data.get('ruleName', ''),
        'fileName': data.get('fileName', ''),
        'line': data.get('line', ''),
    }


class SecretsResultsCollector(Operation):
    """For each scan, fetch /api/results and filter sscs-secret-detection; produce rows for CSV."""

    def execute(self, scans, exception_reporter=None):
        """
        Returns:
            list of (scan, rows) where rows is list of dicts with CSV_HEADER keys.
        """
        results_per_scan = []
        total_secrets = 0
        error_count = 0
        max_workers = getattr(self.config, 'max_workers_results', 10)

        if self.logger:
            self.logger.log("Collecting secrets results for " + str(len(scans)) + " scans...")
        if self.config.debug:
            print("\nCollecting secrets results for", len(scans), "scans...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_scan = {
                executor.submit(self._fetch_secrets_for_scan, scan, exception_reporter): scan
                for scan in scans
            }
            for future in as_completed(future_to_scan):
                scan = future_to_scan[future]
                try:
                    result = future.result()
                    if result is None:
                        error_count += 1
                        continue
                    rows, total_in_scan = result
                    results_per_scan.append((scan, rows))
                    secrets_in_scan = len(rows)
                    total_secrets += secrets_in_scan
                    if self.logger:
                        self.logger.log(
                            "  " + scan.project_name + " (scan " + scan.scan_id + "): "
                            + "total results from scan: " + str(total_in_scan) + "; "
                            + "secrets in scan: " + str(secrets_in_scan) + "; "
                            + "total secrets so far: " + str(total_secrets)
                        )
                    if self.progress:
                        self.progress.update(1)
                        self.progress.set_postfix(secrets=total_secrets, last_scan_results=secrets_in_scan)
                except Exception as e:
                    error_count += 1
                    if self.logger:
                        self.logger.log("ERROR: Failed to collect results for " + scan.project_name + ": " + str(e))
                    if exception_reporter:
                        exception_reporter.add_results_error(scan.project_name, scan.scan_id, str(e))
                    if self.progress:
                        self.progress.update(1)

        if self.logger:
            self.logger.log("Collected " + str(total_secrets) + " total results from " + str(len(results_per_scan)) + " scans (" + str(error_count) + " errors)")
        if self.config.debug:
            print("Collected", total_secrets, "total results from", len(results_per_scan), "scans")
        return results_per_scan

    def _fetch_secrets_for_scan(self, scan, exception_reporter):
        """Fetch all paginated results for scan, filter by type sscs-secret-detection.
        Returns (rows, total_results_in_scan) or None on error.
        """
        try:
            params = {'scan-id': scan.scan_id}
            all_items = self.api_client.get_paginated(
                '/api/results',
                params=params,
                project_name=scan.project_name,
                scan_id=scan.scan_id
            )
            if all_items is None:
                if exception_reporter:
                    exception_reporter.add_results_error(scan.project_name, scan.scan_id, "API returned no data")
                return None
            total_in_scan = len(all_items)
            rows = []
            for item in all_items:
                if not isinstance(item, dict):
                    continue
                raw_type = item.get('type')
                item_type = (raw_type if isinstance(raw_type, str) else str(raw_type or '')).strip()
                if item_type != SECRETS_TYPE:
                    continue
                rows.append(_result_to_row(scan, item))
            return (rows, total_in_scan)
        except Exception as e:
            if exception_reporter:
                exception_reporter.add_results_error(scan.project_name, scan.scan_id, str(e))
            return None
