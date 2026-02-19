"""Find the most recent secrets (microengines 2ms) scan per project."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from src.operations.base import Operation
from src.models.scan import Scan

def _is_secrets_scan(scan_data):
    """True if microengines status is Completed in statusDetails and metadata.configs has microengines with 2ms true."""
    status_details = scan_data.get('statusDetails') or []
    microengines_completed = False
    for detail in status_details:
        if detail.get('name', '').lower() == 'microengines':
            if detail.get('status') == 'Completed':
                microengines_completed = True
            break
    if not microengines_completed:
        return False
    metadata = scan_data.get('metadata') or {}
    configs = metadata.get('configs') or []
    for cfg in configs:
        if cfg.get('type') == 'microengines':
            value = cfg.get('value')
            if isinstance(value, dict) and value.get('2ms') == 'true':
                return True
    return False

class SecretsScanFinder(Operation):
    """Find the most recent scan per project that has successful secrets (microengines 2ms) scan."""

    def execute(self, projects, exception_reporter=None):
        scans_found = []
        not_found_count = 0
        error_count = 0

        if self.logger:
            self.logger.log("Finding latest secrets scans for " + str(len(projects)) + " projects...")
        if self.config.debug:
            print("\nFinding latest secrets scans for", len(projects), "projects...")

        max_workers = getattr(self.config, 'max_workers_scans', 20)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_project = {
                executor.submit(self._find_latest_secrets_scan, project): project
                for project in projects
            }
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                try:
                    scan = future.result()
                    if scan:
                        scans_found.append(scan)
                        if self.logger:
                            self.logger.log("  Found secrets scan for " + project.name + ": " + scan.scan_id)
                    else:
                        not_found_count += 1
                        if self.logger:
                            self.logger.log("  No secrets scan found for " + project.name)
                        if exception_reporter:
                            exception_reporter.add_project_no_scan(project.name)
                    if self.progress:
                        self.progress.update(1)
                        self.progress.set_postfix(found=len(scans_found), not_found=not_found_count)
                except Exception as e:
                    error_count += 1
                    if self.logger:
                        self.logger.log("ERROR: Failed to find scan for " + project.name + ": " + str(e))
                    if self.config.debug:
                        print("Error finding scan for", project.name, e)
                    if exception_reporter:
                        exception_reporter.add_scan_error(project.name, str(e))
                    if self.progress:
                        self.progress.update(1)
                        self.progress.set_postfix(found=len(scans_found), not_found=not_found_count)

        if self.logger:
            self.logger.log("Scan discovery completed: " + str(len(scans_found)) + " found, " + str(not_found_count) + " not found, " + str(error_count) + " errors")
        if self.config.debug:
            print("Scan discovery completed: found", len(scans_found), "not found", not_found_count, "errors", error_count)
        return scans_found

    def _find_latest_secrets_scan(self, project):
        """Return the most recent scan for this project that qualifies as a secrets scan."""
        params = {
            'project-id': project.id,
            'statuses': 'Completed,Partial',
            'sort': '-created_at',
            'limit': self.config.page_size,
            'offset': 0
        }
        while True:
            response_data = self.api_client.get('/api/scans', params=params)
            if not response_data:
                return None
            scans_list = response_data.get('scans', []) if isinstance(response_data, dict) else (response_data if isinstance(response_data, list) else [])
            if not scans_list:
                return None
            for scan_data in scans_list:
                if _is_secrets_scan(scan_data):
                    return Scan(
                        scan_id=scan_data.get('id'),
                        project_id=scan_data.get('projectId') or project.id,
                        project_name=scan_data.get('projectName') or project.name,
                        branch_name=scan_data.get('branch', ''),
                        created_at=scan_data.get('createdAt')
                    )
            if len(scans_list) < self.config.page_size:
                return None
            params['offset'] = params['offset'] + self.config.page_size
