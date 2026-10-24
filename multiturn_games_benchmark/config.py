"""Configuration management"""

import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional


class Config:
    """Configuration manager for the benchmark"""
    
    def __init__(self, models_config_path):
        """
        Initialize configuration
        
        Args:
            models_config_path: Path to models configuration JSON file
        """
        self.models_config_path = Path(models_config_path)
        self.models = self._load_models_config()
    
    def _load_models_config(self) -> Dict[str, Dict[str, Any]]:
        """Load models configuration from JSON file"""
        if not self.models_config_path.exists():
            raise FileNotFoundError(f"Models config not found: {self.models_config_path}")
        
        with open(self.models_config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific model
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model configuration dictionary
        """
        if model_name not in self.models:
            available = ', '.join(self.models.keys())
            raise ValueError(
                f"Model '{model_name}' not found in config. "
                f"Available models: {available}"
            )
        
        return self.models[model_name]
    
    def list_available_models(self) -> List[str]:
        """Get list of available model names"""
        return list(self.models.keys())
    
    def validate_model_config(self, model_name: str) -> bool:
        """
        Validate that a model configuration is complete and API key is available
        
        Args:
            model_name: Name of the model to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        config = self.get_model_config(model_name)
        
        # Check required fields
        required_fields = ['endpoint', 'model_name']
        for field in required_fields:
            if field not in config:
                raise ValueError(
                    f"Model '{model_name}' config missing required field: {field}"
                )
        
        # Check if API key is available in environment
        if not os.getenv('api_key_env'):
            raise ValueError(
                f"API key not found in environment variable: {'api_key_env'}. "
                f"Please set it before running the benchmark."
            )
        
        return True
