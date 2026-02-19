"""Progress tracking utilities."""

from tqdm import tqdm
import sys

class ProgressTracker:
    """Track and display progress for long-running operations."""

    def __init__(self, debug=False):
        self.debug = debug
        self.current_bar = None

    def create_bar(self, total, description, unit='items'):
        if self.current_bar:
            self.current_bar.close()
        self.current_bar = tqdm(
            total=total,
            desc=description,
            unit=unit,
            ncols=120,
            file=sys.stdout
        )
        return self.current_bar

    def update(self, n=1):
        if self.current_bar:
            self.current_bar.update(n)

    def close(self):
        if self.current_bar:
            self.current_bar.close()
            self.current_bar = None

    def set_postfix(self, **kwargs):
        if self.current_bar:
            self.current_bar.set_postfix(**kwargs)

    def print(self, message):
        if self.current_bar:
            self.current_bar.write(message)
        else:
            print(message)


class StageTracker:
    """Track multi-stage operations."""

    def __init__(self, debug=False):
        self.debug = debug
        self.stats = {}

    def start_stage(self, stage_name):
        print(f"\n{'='*120}")
        print(f"{stage_name}")
        print(f"{'='*120}")
        self.stats[stage_name] = {}

    def end_stage(self, stage_name, **stats):
        self.stats[stage_name].update(stats)
        print(f"\n{stage_name} completed:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")

    def get_stats(self):
        return self.stats
