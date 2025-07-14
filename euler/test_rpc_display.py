#!/usr/bin/env python3
"""
Test du nouveau format d'affichage par position
"""

import os
import sys
from rpc_vault_client import EulerRPCClient, PRODUCTION_ADDRESS

def main():
    print("🧪 Test du nouveau format d'affichage par position")
    print("=" * 60)
    
    # Vérifier la configuration
    ethereum_rpc = os.getenv('ETHEREUM_RPC')
    if not ethereum_rpc:
        print("❌ ETHEREUM_RPC n'est pas configuré")
        print("💡 Configurez ETHEREUM_RPC dans le fichier .env")
        print("   Exemple: ETHEREUM_RPC=https://your-rpc-endpoint.com")
        
        # Utiliser un RPC public pour le test
        print("\n🔄 Utilisation d'un RPC public pour le test...")
        os.environ['ETHEREUM_RPC'] = "https://eth.llamarpc.com"
    
    try:
        print(f"📍 Test avec l'adresse: {PRODUCTION_ADDRESS}")
        
        client = EulerRPCClient()
        result = client.analyze_production_positions_rpc()
        
        if result["success"]:
            print(f"\n✅ Test réussi!")
            print(f"📊 Résumé du test:")
            print(f"   - Positions analysées: {len(result['positions']['deposits']) + len(result['positions']['borrows'])}")
            print(f"   - Dépôts: {len(result['positions']['deposits'])}")
            print(f"   - Emprunts: {len(result['positions']['borrows'])}")
            print(f"   - Vaults analysés: {len(result['vault_info'])}")
        else:
            print(f"❌ Test échoué: {result.get('error', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Erreur pendant le test: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 