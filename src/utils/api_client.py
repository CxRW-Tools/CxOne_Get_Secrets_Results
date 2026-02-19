"""API client with pagination and retry logic."""

import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

class APIClient:
    """HTTP client for CxOne API with pagination and retry support."""

    def __init__(self, base_url, auth_manager, config, debug=False, debug_logger=None):
        self.base_url = base_url
        self.auth = auth_manager
        self.config = config
        self.debug = debug
        self.logger = debug_logger

    def _debug_prefix(self, project_name=None, scan_id=None):
        """Build '[timestamp] project_name scan_id' for debug output."""
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        prefix = f"[{ts}]"
        if project_name is not None:
            prefix += f" {project_name}"
        if scan_id is not None:
            prefix += f" {scan_id}"
        return prefix

    def get_paginated(self, endpoint, params=None, max_results=None, project_name=None, scan_id=None):
        """Fetch all results from a paginated endpoint."""
        all_results = []
        offset = 0
        limit = self.config.page_size
        params = params or {}
        # /api/results: offset = page index (0, 1, 2, ...), limit = page size. Other endpoints: offset = records to skip.
        is_results_endpoint = '/api/results' in endpoint or endpoint.rstrip('/').endswith('results')
        total_count = None  # when set, we keep fetching until we have this many (for results endpoint)

        while True:
            page_params = params.copy()
            page_params['limit'] = limit
            page_params['offset'] = offset

            scan_id_part = f", scan-id={page_params.get('scan-id')}" if 'scan-id' in page_params else ""
            offset_label = "page" if is_results_endpoint else "offset"
            if self.logger:
                self.logger.log(f"API: GET {endpoint} ({offset_label}={offset}, limit={limit}{scan_id_part})", project_name=project_name, scan_id=scan_id)
            if self.debug:
                print(f"{self._debug_prefix(project_name, scan_id)}   Fetching {endpoint} ({offset_label}={offset}, limit={limit}{scan_id_part})...")

            response_data = self.get(endpoint, params=page_params)

            if not response_data:
                break

            if isinstance(response_data, dict):
                # Use totalCount when present so we don't stop early on short/empty pages
                if total_count is None and is_results_endpoint:
                    total_count = response_data.get('totalCount') or response_data.get('total_count')
                if 'projects' in response_data:
                    results = response_data.get('projects', [])
                elif 'scans' in response_data:
                    results = response_data.get('scans', [])
                elif 'results' in response_data:
                    results = response_data.get('results', [])
                elif 'branches' in response_data:
                    results = response_data.get('branches', [])
                elif 'items' in response_data:
                    results = response_data.get('items', [])
                else:
                    results = [response_data]
            elif isinstance(response_data, list):
                results = response_data
            else:
                break

            if not results:
                # No more items this page; stop if we have enough or no totalCount to ask for more
                if total_count is not None and len(all_results) < total_count and self.logger:
                    label = "page" if is_results_endpoint else "offset"
                    self.logger.log(f"API: Empty page at {label}={offset} but totalCount={total_count}; stopping (have {len(all_results)})", project_name=project_name, scan_id=scan_id)
                break

            all_results.extend(results)

            retrieved_scan_part = f" [scan-id={page_params['scan-id']}]" if 'scan-id' in page_params else ""
            total_count_part = f", totalCount={total_count}" if total_count is not None else ""
            if self.logger:
                self.logger.log(f"API: Retrieved {len(results)} items (total so far: {len(all_results)}{total_count_part}){retrieved_scan_part}", project_name=project_name, scan_id=scan_id)
            if self.debug:
                print(f"{self._debug_prefix(project_name, scan_id)}   Retrieved {len(results)} items (total: {len(all_results)}{total_count_part}){retrieved_scan_part}")

            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break

            # Stop if we've received all we need
            if total_count is not None and len(all_results) >= total_count:
                break
            if len(results) < limit and (total_count is None or len(all_results) >= total_count):
                break

            # Results API: offset = page index (increment by 1). Other APIs: offset = records to skip (increment by limit).
            if is_results_endpoint:
                offset += 1
            else:
                offset += limit

        return all_results

    def get(self, endpoint, params=None):
        """Make a GET request with retry logic."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.config.max_retries):
            try:
                headers = self.auth.get_headers()
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.config.request_timeout
                )

                if response.status_code == 429:
                    wait_time = 30
                    if self.debug:
                        print(f"    Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    if self.logger:
                        self.logger.log(f"API: Timeout on {url}. Retrying in {wait_time}s...")
                    if self.debug:
                        print(f"    Timeout. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    if self.logger:
                        self.logger.log(f"API: Request timed out after {self.config.max_retries} attempts: {url}")
                    return None

            except requests.exceptions.RequestException as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    if self.logger:
                        self.logger.log(f"API: Error on {url}: {e}. Retrying in {wait_time}s...")
                    if self.debug:
                        print(f"    Error: {e}. Retrying...")
                    time.sleep(wait_time)
                else:
                    if self.logger:
                        self.logger.log(f"API: Request failed after {self.config.max_retries} attempts: {url} - {e}")
                    return None

        return None
