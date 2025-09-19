"""
Configuration loader with environment variable support
"""

import os
import yaml
import re
from typing import Any, Dict

def load_yaml_with_env(path: str) -> Dict[str, Any]:
    """
    Load YAML file with environment variable substitution
    
    Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax
    """
    with open(path, 'r') as f:
        content = f.read()
    
    # Replace environment variables
    def replace_env_var(match):
        var_expr = match.group(1)
        if ':' in var_expr:
            var_name, default_value = var_expr.split(':', 1)
        else:
            var_name = var_expr
            default_value = None
        
        return os.getenv(var_name, default_value or '')
    
    # Pattern to match ${VAR} or ${VAR:default}
    env_pattern = re.compile(r'\$\{([^}]+)\}')
    content = env_pattern.sub(replace_env_var, content)
    
    return yaml.safe_load(content)


