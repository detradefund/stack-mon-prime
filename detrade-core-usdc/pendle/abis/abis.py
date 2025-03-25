import json
from pathlib import Path

# Load ABIs from JSON files
def load_abi(filename):
    with open(Path(__file__).parent / filename, 'r') as f:
        return json.load(f)

# Les deux ABIs sont identiques, on peut utiliser l'un ou l'autre comme référence
PT_ABI = load_abi('PT-eUSDE-29MAY2025.json')  

__all__ = ['PT_ABI'] 