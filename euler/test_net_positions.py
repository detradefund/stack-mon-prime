#!/usr/bin/env python3
"""
Test pour le calcul du net par position avec conversion pufETH->WETH
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from euler.rpc_vault_client import EulerRPCClient

def test_net_positions():
    """Test du calcul du net par position"""
    
    print("🧪 Test du calcul du net par position")
    print("=" * 60)
    print("📍 Adresse testée: 0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C")
    print("🌐 Conversion pufETH → WETH via CoW Protocol")
    print("-" * 60)
    
    try:
        # Initialiser le client
        client = EulerRPCClient()
        
        # Calculer le net par position
        result = client.get_balances()
        
        if result and result.get('euler') and result['euler'].get('ethereum'):
            print(f"\n✅ Test réussi!")
            
            # Afficher les détails
            euler_data = result['euler']['ethereum']
            if 'net_position' in euler_data:
                net_pos = euler_data['net_position']
                if 'totals' in net_pos:
                    net_total = net_pos['totals']['formatted']
                    print(f"📊 Net total: {net_total} ETH")
                
                # Afficher les détails par subaccount
                if 'subaccounts' in net_pos:
                    print(f"\n📝 Détails par subaccount:")
                    for subaccount_addr, net_data in net_pos['subaccounts'].items():
                        print(f"   👤 {subaccount_addr}:")
                        print(f"      - Net: {net_data['net_eth']} ETH")
        else:
            print(f"\n❌ Test échoué: Aucune position trouvée")
            return 1
            
    except Exception as e:
        print(f"\n❌ Erreur pendant le test: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(test_net_positions()) 