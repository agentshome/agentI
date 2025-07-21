import yaml
import os

# Get the project root directory (which is the parent of the 'utils' directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'config.yaml')
EXAMPLE_CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'config.example.yaml')

def load_config():
    """Loads the model and API configuration from config.yaml."""
    if not os.path.exists(CONFIG_PATH):
        if not os.path.exists(EXAMPLE_CONFIG_PATH):
            raise FileNotFoundError("Neither config.yaml nor config.example.yaml were found.")
        # If the user hasn't created their own config, use the example as a default
        print("Warning: config.yaml not found. Using config.example.yaml as a fallback.")
        config_file_to_load = EXAMPLE_CONFIG_PATH
    else:
        config_file_to_load = CONFIG_PATH

    with open(config_file_to_load, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

config = load_config()

def get_active_model_config(model_type: str):
    """Gets the configuration for the currently active model of a given type (llm or vlm)."""
    active_model_name = config['active_models'][model_type]
    model_config = config[f'{model_type}s'][active_model_name]
    return model_config
