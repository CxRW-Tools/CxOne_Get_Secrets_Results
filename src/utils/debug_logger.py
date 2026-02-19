"""Debug logging to file with live updates."""

from datetime import datetime

class DebugLogger:
    """Logger that writes debug output to file and optionally console."""

    def __init__(self, log_file_path, console_debug=False):
        self.log_file_path = log_file_path
        self.console_debug = console_debug
        self.file_handle = None
        try:
            self.file_handle = open(log_file_path, 'w', encoding='utf-8', buffering=1)
            self.log("Debug log started: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            self.log("=" * 120)
        except Exception as e:
            print("Warning: Could not open debug log file:", e)

    def log(self, message, project_name=None, scan_id=None):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        prefix = "[" + timestamp + "]"
        if project_name is not None:
            prefix += " " + str(project_name)
        if scan_id is not None:
            prefix += " " + str(scan_id)
        log_line = prefix + " " + message
        if self.file_handle:
            try:
                self.file_handle.write(log_line + "\n")
                self.file_handle.flush()
            except Exception as e:
                print("Warning: Failed to write to debug log:", e)
        if self.console_debug:
            print(message)

    def close(self):
        if self.file_handle:
            try:
                self.log("=" * 120)
                self.log("Debug log ended: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                self.file_handle.close()
            except Exception:
                pass
            self.file_handle = None

    def __del__(self):
        self.close()
