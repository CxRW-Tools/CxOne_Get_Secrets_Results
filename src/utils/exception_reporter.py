"""Exception and summary reporting utilities."""

import os
from datetime import datetime

class ExceptionReporter:
    """Track and report exceptions and summaries for secrets results execution."""

    def __init__(self):
        self.projects_no_scan = []
        self.scan_errors = []
        self.results_errors = []
        self.api_errors = []
        self.general_warnings = []
        self.stats = {
            'total_projects': 0,
            'scans_found': 0,
            'scans_not_found': 0,
            'secrets_count': 0,
            'execution_time': '0h 0m 0s',
            'output_file': '',
            'output_size': ''
        }

    def add_project_no_scan(self, project_name):
        self.projects_no_scan.append({'project': project_name})

    def add_scan_error(self, project_name, error_message):
        self.scan_errors.append({'project': project_name, 'error': error_message})

    def add_results_error(self, project_name, scan_id, error_message):
        self.results_errors.append({
            'project': project_name,
            'scan_id': scan_id,
            'error': error_message
        })

    def add_api_error(self, endpoint, error_message):
        self.api_errors.append({'endpoint': endpoint, 'error': error_message})

    def add_general_warning(self, category, message):
        self.general_warnings.append({'category': category, 'message': message})

    def update_stats(self, **kwargs):
        self.stats.update(kwargs)

    def generate_report(self, output_csv_path):
        """Generate and save the execution report."""
        report_path = os.path.splitext(output_csv_path)[0] + '_report.txt'
        lines = []
        lines.append("=" * 80)
        lines.append("CxOne Secrets Results - Execution Report")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("=" * 80)
        lines.append("SUMMARY STATISTICS")
        lines.append("=" * 80)
        lines.append(f"Total Projects:     {self.stats['total_projects']:,}")
        lines.append(f"Scans Found:        {self.stats['scans_found']:,}")
        lines.append(f"Scans Not Found:    {self.stats['scans_not_found']:,}")
        lines.append(f"Secrets Count:     {self.stats['secrets_count']:,}")
        lines.append(f"Execution Time:     {self.stats['execution_time']}")
        lines.append(f"Output File:        {self.stats['output_file']}")
        if self.stats.get('output_size'):
            lines.append(f"Output Size:        {self.stats['output_size']}")
        lines.append("")

        if self.projects_no_scan:
            lines.append("=" * 80)
            lines.append(f"PROJECTS WITHOUT SECRETS SCAN ({len(self.projects_no_scan)})")
            lines.append("=" * 80)
            for item in self.projects_no_scan:
                lines.append(f"  - {item['project']}")
            lines.append("")

        if self.scan_errors:
            lines.append("=" * 80)
            lines.append(f"SCAN ERRORS ({len(self.scan_errors)})")
            lines.append("=" * 80)
            for idx, err in enumerate(self.scan_errors, 1):
                lines.append(f"{idx}. Project: {err['project']}")
                lines.append(f"   Error: {err['error']}")
            lines.append("")

        if self.results_errors:
            lines.append("=" * 80)
            lines.append(f"RESULTS FETCH ERRORS ({len(self.results_errors)})")
            lines.append("=" * 80)
            for idx, err in enumerate(self.results_errors, 1):
                lines.append(f"{idx}. Project: {err['project']}, Scan: {err['scan_id']}")
                lines.append(f"   Error: {err['error']}")
            lines.append("")

        if self.api_errors:
            lines.append("=" * 80)
            lines.append(f"API ERRORS ({len(self.api_errors)})")
            lines.append("=" * 80)
            for idx, err in enumerate(self.api_errors, 1):
                lines.append(f"{idx}. Endpoint: {err['endpoint']}")
                lines.append(f"   Error: {err['error']}")
            lines.append("")

        if not (self.projects_no_scan or self.scan_errors or self.results_errors or self.api_errors or self.general_warnings):
            lines.append("=" * 80)
            lines.append("NO ERRORS OR WARNINGS")
            lines.append("=" * 80)
            lines.append("All operations completed successfully!")
            lines.append("")

        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return report_path
