# api_key_manager.py
import os
from dotenv import load_dotenv

load_dotenv()

class EtherscanAPIKeyManager:
    def __init__(self):
        self.api_keys = [
            os.getenv('ETHERSCAN_API_KEY'),
            os.getenv('ETHERSCAN_API_KEY_2'),
            os.getenv('ETHERSCAN_API_KEY_3')
        ]
        self.current_key_index = 0

    def get_current_key(self):
        return self.api_keys[self.current_key_index]

    def switch_key(self):
        previous_key = self.get_current_key()
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        new_key = self.get_current_key()
        print(f"Switched from API key: {previous_key} to API key: {new_key}")

etherscan_api_key_manager = EtherscanAPIKeyManager()
