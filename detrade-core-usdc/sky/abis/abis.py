import json
from pathlib import Path

# Load ABIs from JSON files
def load_abi(filename):
    with open(Path(__file__).parent / filename, 'r') as f:
        return json.load(f)

SUSDS_ABI = load_abi('sUSDS.json')