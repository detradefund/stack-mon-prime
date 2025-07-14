#!/usr/bin/env python3
"""
Script principal d'analyse des positions Euler v2 avec RPC
Utilise la configuration ETHEREUM_RPC du fichier .env du projet
"""

import os
import sys
from rpc_vault_client import EulerRPCClient, PRODUCTION_ADDRESS

def main():
    print("🚀 Analyse des positions Euler v2 - Adresse de production")
    print("=" * 70)
    
    # Vérifier la configuration
    ethereum_rpc = os.getenv('ETHEREUM_RPC')
    if not ethereum_rpc:
        print("❌ ETHEREUM_RPC n'est pas configuré")
        print("💡 Veuillez configurer ETHEREUM_RPC dans le fichier .env à la racine du projet")
        print("   Exemple dans .env:")
        print("   ETHEREUM_RPC=https://your-rpc-endpoint.com")
        return 1
    
    print(f"📍 Adresse de production: {PRODUCTION_ADDRESS}")
    print(f"🌐 RPC Ethereum: {ethereum_rpc[:30]}...")
    
    try:
        # Créer le client RPC
        client = EulerRPCClient()
        
        # Analyser les positions de production
        result = client.analyze_production_positions_rpc()
        
        if result["success"]:
            print("\n✅ Analyse terminée avec succès!")
            return 0
        else:
            print(f"\n❌ Erreur lors de l'analyse: {result.get('error', 'Erreur inconnue')}")
            return 1
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 