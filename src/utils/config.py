import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        """Initialize configuration with default values."""
        # Authentication
        self.base_url = None
        self.tenant_name = None
        self.api_key = None

        # General
        self.debug = False

        # Threading
        self.max_workers_projects = 5
        self.max_workers_scans = 20
        self.max_workers_results = 10

        # API settings
        self.max_retries = 3
        self.retry_delay = 2.0
        self.request_timeout = 60
        self.page_size = 100

        # File paths
        self.output_directory = "./output"
        self.temp_directory = "./temp"

        # Output settings (secrets results)
        self.output_filename_template = "secrets_results_{tenant}_{timestamp}.csv"
        self.include_timestamp = True

        # Memory management
        self.temp_file_cleanup = True

        # Error handling
        self.continue_on_errors = True
        self.log_errors_to_file = True

    @classmethod
    def from_args(cls, args):
        """Create configuration from command line arguments."""
        config = cls()
        if hasattr(args, 'base_url') and args.base_url:
            config.base_url = args.base_url
        if hasattr(args, 'tenant_name') and args.tenant_name:
            config.tenant_name = args.tenant_name
        if hasattr(args, 'api_key') and args.api_key:
            config.api_key = args.api_key
        if hasattr(args, 'debug') and args.debug:
            config.debug = args.debug
        if hasattr(args, 'max_workers') and args.max_workers:
            config.max_workers_results = args.max_workers
        if hasattr(args, 'output_dir') and args.output_dir:
            config.output_directory = args.output_dir
        return config

    @classmethod
    def from_env(cls, env_file='.env'):
        """Create configuration from environment variables."""
        load_dotenv(env_file)

        config = cls()
        config.base_url = os.getenv('CXONE_BASE_URL')
        config.tenant_name = os.getenv('CXONE_TENANT')
        config.api_key = os.getenv('CXONE_API_KEY')
        config.debug = os.getenv('CXONE_DEBUG', '').lower() == 'true'

        if os.getenv('CXONE_MAX_WORKERS'):
            config.max_workers_results = int(os.getenv('CXONE_MAX_WORKERS'))
        if os.getenv('CXONE_OUTPUT_DIR'):
            config.output_directory = os.getenv('CXONE_OUTPUT_DIR')

        return config

    def validate(self):
        """Validate the configuration. Returns (bool, str)."""
        if not self.base_url:
            return False, "Base URL is required"
        if not self.tenant_name:
            return False, "Tenant name is required"
        if not self.api_key:
            return False, "API key is required"
        return True, None
