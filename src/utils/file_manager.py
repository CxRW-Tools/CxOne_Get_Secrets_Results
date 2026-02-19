"""File management utilities."""

import os
from datetime import datetime

class FileManager:
    """Manage temporary and output files."""

    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug
        self.temp_files = []

    def setup_directories(self):
        os.makedirs(self.config.temp_directory, exist_ok=True)
        os.makedirs(self.config.output_directory, exist_ok=True)
        if self.debug:
            print("Created directories:")
            print("  - Temp:", self.config.temp_directory)
            print("  - Output:", self.config.output_directory)

    def get_output_file_path(self):
        if not hasattr(self, '_output_path'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = self.config.output_filename_template.format(
                tenant=self.config.tenant_name,
                timestamp=timestamp
            )
            self._output_path = os.path.join(self.config.output_directory, filename)
        return self._output_path

    def get_debug_log_path(self):
        output_path = self.get_output_file_path()
        return os.path.splitext(output_path)[0] + '_debug.txt'

    def cleanup_temp_files(self):
        if not getattr(self.config, 'temp_file_cleanup', True):
            return
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                if self.debug:
                    print("Failed to remove", file_path, e)
        try:
            if os.path.exists(self.config.temp_directory) and not os.listdir(self.config.temp_directory):
                os.rmdir(self.config.temp_directory)
        except Exception:
            pass
