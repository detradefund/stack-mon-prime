#!/usr/bin/env python3
"""
Version simplifiée du client Euler RPC utilisant la configuration .env du projet
"""

import os
import sys
from rpc_vault_client import EulerRPCClient, PRODUCTION_ADDRESS

def main():
    print("🚀 Analyse Euler v2 - Client RPC")
    print("=" * 60)
    
    # Vérifier que ETHEREUM_RPC est configuré
    ethereum_rpc = os.getenv('ETHEREUM_RPC')
    if not ethereum_rpc:
        print("❌ ETHEREUM_RPC n'est pas configuré")
        print("💡 Veuillez configurer ETHEREUM_RPC dans le fichier .env à la racine du projet")
        print("   Exemple: ETHEREUM_RPC=https://your-rpc-endpoint.com")
        return 1
    
    try:
        client = EulerRPCClient()
        client.analyze_production_positions_rpc()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 