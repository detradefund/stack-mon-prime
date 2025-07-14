#!/usr/bin/env python3
"""
Test script pour tester la nouvelle fonctionnalité de récupération des balances des vaults
avec balanceOf() et asset() pour chaque subaccount
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

from rpc_vault_client import EulerRPCClient, PRODUCTION_ADDRESS

def test_vault_balances():
    """Test la récupération des balances des vaults avec balanceOf et asset"""
    
    print("🧪 Test de récupération des balances des vaults")
    print("=" * 60)
    
    # Vérifier la configuration RPC
    ethereum_rpc = os.getenv('ETHEREUM_RPC')
    if not ethereum_rpc:
        print("❌ ETHEREUM_RPC n'est pas configuré")
        print("💡 Configurez ETHEREUM_RPC dans le fichier .env")
        return 1
    
    print(f"📍 Adresse testée: {PRODUCTION_ADDRESS}")
    print(f"🌐 RPC Ethereum: {ethereum_rpc[:30]}...")
    print("-" * 60)
    
    try:
        # Créer le client RPC
        client = EulerRPCClient()
        
        # Tester la nouvelle méthode de récupération des balances
        print("\n🔄 Test de get_all_vault_balances_for_positions()...")
        result = client.get_all_vault_balances_for_positions()
        
        if result["success"]:
            print(f"\n✅ Test réussi!")
            print(f"📊 Résumé des résultats:")
            print(f"   - Adresse: {result['address']}")
            print(f"   - Total subaccounts: {result['summary']['total_subaccounts']}")
            print(f"   - Total positions: {result['summary']['total_positions']}")
            print(f"   - Total dépôts: {result['summary']['total_deposits']}")
            print(f"   - Total emprunts: {result['summary']['total_borrows']}")
            print(f"   - Positions non-nulles: {result['summary']['non_zero_positions']}")
            
            # Afficher les détails des subaccounts
            if result['subaccounts']:
                print(f"\n📝 Détails des subaccounts et positions:")
                for subaccount_addr, subaccount_data in result['subaccounts'].items():
                    print(f"\n   👤 Subaccount: {subaccount_addr}")
                    
                    # Afficher les dépôts
                    deposits = subaccount_data['positions']['deposits']
                    if deposits:
                        print(f"      💰 Dépôts ({len(deposits)}):")
                        for deposit in deposits:
                            balance = deposit.get('balance', '0')
                            balance_type = deposit.get('balance_type', 'shares')
                            symbol = deposit.get('symbol', 'Unknown')
                            underlying_balance = deposit.get('underlying_balance')
                            underlying_symbol = deposit.get('underlying_asset_info', {}).get('symbol', 'Unknown')
                            if underlying_balance:
                                print(f"         - {symbol}: {balance} {balance_type} = {underlying_balance} {underlying_symbol}")
                            else:
                                print(f"         - {symbol}: {balance} {balance_type}")
                    
                    # Afficher les emprunts
                    borrows = subaccount_data['positions']['borrows']
                    if borrows:
                        print(f"      💸 Emprunts ({len(borrows)}):")
                        for borrow in borrows:
                            balance = borrow.get('balance', '0')
                            balance_type = borrow.get('balance_type', 'debt')
                            symbol = borrow.get('symbol', 'Unknown')
                            underlying_symbol = borrow.get('underlying_asset_info', {}).get('symbol', 'Unknown')
                            print(f"         - {symbol}: {balance} {balance_type} ({underlying_symbol})")
            else:
                print("\n⚠️  Aucun subaccount trouvé")
            
        else:
            print(f"\n❌ Test échoué: {result.get('error', 'Erreur inconnue')}")
            return 1
        
        print("\n" + "=" * 60)
        print("🎉 Test des balances de vaults terminé avec succès!")
        
    except Exception as e:
        print(f"\n❌ Erreur pendant le test: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

def main():
    """Point d'entrée principal"""
    return test_vault_balances()

if __name__ == "__main__":
    sys.exit(main()) 