"""API client with pagination and retry logic."""

import time
import sys
import requests
from typing import List, Dict, Any, Optional

class APIClient:
    """HTTP client for CxOne API with pagination and retry support."""

    def __init__(self, base_url, auth_manager, config, debug=False, debug_logger=None):
        self.base_url = base_url
        self.auth = auth_manager
        self.config = config
        self.debug = debug
        self.logger = debug_logger

    def get_paginated(self, endpoint, params=None, max_results=None):
        """Fetch all results from a paginated endpoint."""
        all_results = []
        offset = 0
        limit = self.config.page_size
        params = params or {}

        while True:
            page_params = params.copy()
            page_params['limit'] = limit
            page_params['offset'] = offset

            if self.logger:
                self.logger.log(f"API: GET {endpoint} (offset={offset}, limit={limit})")
            if self.debug:
                print(f"  Fetching {endpoint} (offset={offset}, limit={limit})...")

            response_data = self.get(endpoint, params=page_params)

            if not response_data:
                break

            if isinstance(response_data, dict):
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
                break

            all_results.extend(results)

            if self.logger:
                self.logger.log(f"API: Retrieved {len(results)} items (total so far: {len(all_results)})")
            if self.debug:
                print(f"    Retrieved {len(results)} items (total: {len(all_results)})")

            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break

            if len(results) < limit:
                break

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
