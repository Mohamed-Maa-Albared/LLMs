import json
import os
import pathlib


class ConfigLoader:
    def __init__(self):
        self.config_file = None
        self.config = self.load_config()

    def get_config_root(self):
        return pathlib.Path(
            pathlib.Path(os.path.realpath(__file__)).parents[2].resolve(), "configs"
        )

    def load_config(self):
        """Load the entire configuration from the JSON file."""
        self.config_file = f"{self.get_config_root()}/app_config.json"
        if not os.path.exists(self.config_file):
            print(f"Config file {self.config_file} not found. Using empty config.")
            return {}

        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {self.config_file}. Using empty config.")
            return {}

    def get_section(self, section_name):
        """Get a specific section from the configuration."""
        return self.config.get(section_name, {})

    def update_section(self, section_name, data):
        """Update a specific section in the configuration."""
        self.config[section_name] = data

    def save_config(self):
        """Save the current configuration back to the JSON file."""
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)

    def add_item_to_section(self, section_name, item):
        """Add an item to a list in a specific section."""
        if section_name not in self.config:
            self.config[section_name] = []
        self.config[section_name].append(item)

    def remove_item_from_section(
        self, section_name, item_identifier, identifier_key="name"
    ):
        """Remove an item from a list in a specific section based on an identifier."""
        if section_name in self.config and isinstance(self.config[section_name], list):
            self.config[section_name] = [
                item
                for item in self.config[section_name]
                if item.get(identifier_key) != item_identifier
            ]
