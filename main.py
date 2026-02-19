#!/usr/bin/env python3
"""
CxOne Secrets Results

For each project, finds the most recent scan with successful secrets (microengines 2ms) scan,
collects all sscs-secret-detection results, and outputs a single CSV.
"""

import sys
import argparse
import time
import csv
import os

from src.utils.auth import AuthManager
from src.utils.config import Config
from src.utils.api_client import APIClient
from src.utils.progress import ProgressTracker, StageTracker
from src.utils.file_manager import FileManager
from src.utils.exception_reporter import ExceptionReporter
from src.utils.debug_logger import DebugLogger
from src.operations.project_discovery import ProjectDiscovery
from src.operations.secrets_scan_finder import SecretsScanFinder
from src.operations.secrets_results_collector import SecretsResultsCollector, CSV_HEADER


def parse_args():
    parser = argparse.ArgumentParser(
        description='CxOne Secrets Results - Collect secrets scan results from all projects'
    )
    parser.add_argument('--env-file', help='Path to environment file (default: .env)')
    parser.add_argument('--base-url', help='Region Base URL')
    parser.add_argument('--tenant-name', help='Tenant name')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--max-workers', type=int, help='Maximum worker threads for results collection')
    parser.add_argument('--output-dir', help='Output directory for final CSV')
    return parser.parse_args()


def write_secrets_csv(output_path, results_per_scan):
    """Write a single CSV with header CSV_HEADER and one row per secret."""
    total_rows = 0
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        for _scan, rows in results_per_scan:
            for row in rows:
                writer.writerow(row)
                total_rows += 1
    return total_rows


def get_file_size(file_path):
    try:
        size_bytes = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    except Exception:
        return "Unknown"


def main():
    start_time = time.time()
    args = parse_args()

    env_file = getattr(args, 'env_file', None) or '.env'
    config = Config.from_env(env_file)
    if args.base_url:
        config.base_url = args.base_url
    if args.tenant_name:
        config.tenant_name = args.tenant_name
    if args.api_key:
        config.api_key = args.api_key
    if args.debug:
        config.debug = args.debug
    if args.max_workers:
        config.max_workers_results = args.max_workers
    if args.output_dir:
        config.output_directory = args.output_dir

    is_valid, error = config.validate()
    if not is_valid:
        print("Configuration error:", error)
        sys.exit(1)

    print("=" * 120)
    print("CxOne Secrets Results")
    print("=" * 120)
    print("Tenant:", config.tenant_name)
    print("Base URL:", config.base_url)
    print("Output Directory:", config.output_directory)
    print("=" * 120)

    auth_manager = AuthManager(
        base_url=config.base_url,
        tenant_name=config.tenant_name,
        api_key=config.api_key,
        debug=config.debug
    )

    try:
        auth_manager.ensure_authenticated()
        if config.debug:
            print("\nSuccessfully authenticated with CxOne")

        file_manager = FileManager(config, config.debug)
        file_manager.setup_directories()

        debug_log_path = file_manager.get_debug_log_path()
        debug_logger = DebugLogger(debug_log_path, console_debug=config.debug)
        debug_logger.log("CxOne Secrets Results - Debug Log")
        debug_logger.log("Tenant: " + config.tenant_name)
        debug_logger.log("Base URL: " + config.base_url)

        api_client = APIClient(config.base_url, auth_manager, config, config.debug, debug_logger)
        progress_tracker = ProgressTracker(config.debug)
        stage_tracker = StageTracker(config.debug)
        exception_reporter = ExceptionReporter()

        # Stage 1: Discover projects
        stage_tracker.start_stage("Stage 1: Discovering Projects")
        debug_logger.log("Starting Stage 1: Project Discovery")
        project_discovery = ProjectDiscovery(config, auth_manager, api_client, progress_tracker, debug_logger)
        projects = project_discovery.execute()
        if not projects:
            print("No projects found. Exiting.")
            debug_logger.log("ERROR: No projects found")
            debug_logger.close()
            sys.exit(0)
        debug_logger.log("Found " + str(len(projects)) + " projects")
        stage_tracker.end_stage("Stage 1: Discovering Projects", total_projects=len(projects))

        # Stage 2: Find latest secrets scan per project
        stage_tracker.start_stage("Stage 2: Finding Latest Secrets Scans")
        debug_logger.log("Starting Stage 2: Secrets Scan Finding for " + str(len(projects)) + " projects")
        progress_bar = progress_tracker.create_bar(len(projects), "Finding secrets scans", "projects")
        scan_finder = SecretsScanFinder(config, auth_manager, api_client, progress_tracker, debug_logger)
        scans = scan_finder.execute(projects, exception_reporter)
        progress_tracker.close()
        if not scans:
            print("No secrets scans found. Exiting.")
            debug_logger.log("ERROR: No secrets scans found")
            debug_logger.close()
            sys.exit(0)
        debug_logger.log("Found " + str(len(scans)) + " secrets scans")
        stage_tracker.end_stage(
            "Stage 2: Finding Latest Secrets Scans",
            scans_found=len(scans),
            projects_without_scan=len(projects) - len(scans)
        )

        # Stage 3: Collect secrets results per scan
        stage_tracker.start_stage("Stage 3: Collecting Secrets Results")
        debug_logger.log("Starting Stage 3: Results collection for " + str(len(scans)) + " scans")
        progress_bar = progress_tracker.create_bar(len(scans), "Collecting results", "scans")
        results_collector = SecretsResultsCollector(config, auth_manager, api_client, progress_tracker, debug_logger)
        results_per_scan = results_collector.execute(scans, exception_reporter)
        progress_tracker.close()
        total_secrets = sum(len(rows) for _, rows in results_per_scan)
        debug_logger.log("Collected " + str(total_secrets) + " secrets from " + str(len(results_per_scan)) + " scans")
        stage_tracker.end_stage("Stage 3: Collecting Secrets Results", total_secrets=total_secrets, scans_processed=len(results_per_scan))

        # Stage 4: Write CSV
        stage_tracker.start_stage("Stage 4: Writing CSV")
        output_path = file_manager.get_output_file_path()
        debug_logger.log("Writing CSV to " + output_path)
        total_rows = write_secrets_csv(output_path, results_per_scan)
        stage_tracker.end_stage("Stage 4: Writing CSV", total_rows=total_rows, output_file=output_path)

        # Cleanup
        if config.temp_file_cleanup:
            file_manager.cleanup_temp_files()

        # Report and summary
        elapsed_time = time.time() - start_time
        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)
        execution_time = f"{hours}h {minutes}m {seconds}s"

        exception_reporter.update_stats(
            total_projects=len(projects),
            scans_found=len(scans),
            scans_not_found=len(projects) - len(scans),
            secrets_count=total_rows,
            execution_time=execution_time,
            output_file=output_path,
            output_size=get_file_size(output_path)
        )
        report_path = exception_reporter.generate_report(output_path)

        debug_logger.log("=" * 120)
        debug_logger.log("EXECUTION COMPLETED")
        debug_logger.log("Total projects: " + str(len(projects)))
        debug_logger.log("Scans found: " + str(len(scans)))
        debug_logger.log("Total secrets: " + str(total_rows))
        debug_logger.log("Execution time: " + execution_time)
        debug_logger.log("Output file: " + output_path)
        debug_logger.log("=" * 120)
        debug_logger.close()

        print("\n" + "=" * 120)
        print("EXECUTION SUMMARY")
        print("=" * 120)
        print("Successfully completed!")
        print("\nStatistics:")
        print("  - Total projects:", len(projects))
        print("  - Scans with secrets:", len(scans))
        print("  - Total secrets:", total_rows)
        print("\nOutput:")
        print("  - Data File:", output_path)
        print("  - Size:", get_file_size(output_path))
        print("  - Report File:", report_path)
        print("  - Debug Log:", debug_log_path)
        print("\nExecution time:", execution_time)
        print("=" * 120)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        if 'debug_logger' in locals():
            debug_logger.log("INTERRUPTED: Operation cancelled by user")
            debug_logger.close()
        sys.exit(1)
    except Exception as e:
        print("\nError:", e)
        if 'debug_logger' in locals():
            debug_logger.log("FATAL ERROR: " + str(e))
            if config.debug:
                import traceback
                debug_logger.log(traceback.format_exc())
            debug_logger.close()
        elif config.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
