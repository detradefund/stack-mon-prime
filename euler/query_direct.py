#!/usr/bin/env python3
"""
Script direct pour interroger les positions actives sur Euler v2
"""

import sys
from query_active_positions import EulerGraphQLClient

def main():
    # Prendre l'adresse depuis les arguments ou demander à l'utilisateur
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        address = input("Entrez l'adresse Ethereum à interroger: ").strip()
    
    if not address:
        print("❌ Adresse requise")
        return
    
    # Créer le client et faire la requête
    client = EulerGraphQLClient()
    
    print(f"\n🔍 Interrogation des positions actives pour: {address}")
    print(f"📡 Endpoint Euler v2: {client.endpoint}")
    print("-" * 80)
    
    result = client.query_active_positions(address)
    
    if result and result.get('trackingActiveAccount'):
        account = result['trackingActiveAccount']
        
        print("✅ Positions trouvées!")
        print(f"📍 Adresse principale: {account['mainAddress']}")
        
        deposits = account.get('deposits', [])
        borrows = account.get('borrows', [])
        
        print(f"\n💰 Dépôts (Deposits): {len(deposits)} positions")
        if deposits:
            for i, deposit_id in enumerate(deposits, 1):
                print(f"   {i}. {deposit_id}")
        else:
            print("   Aucun dépôt")
        
        print(f"\n🏦 Emprunts (Borrows): {len(borrows)} positions")
        if borrows:
            for i, borrow_id in enumerate(borrows, 1):
                print(f"   {i}. {borrow_id}")
        else:
            print("   Aucun emprunt")
        
        # Résumé
        print(f"\n📊 Résumé:")
        print(f"   - Total positions actives: {len(deposits) + len(borrows)}")
        print(f"   - Positions de dépôt: {len(deposits)}")
        print(f"   - Positions d'emprunt: {len(borrows)}")
        
        if len(deposits) > 0 or len(borrows) > 0:
            print(f"   - Statut: 🟢 Actif sur Euler v2")
        else:
            print(f"   - Statut: 🔴 Aucune position active")
            
    else:
        print("❌ Aucune position active trouvée pour cette adresse")

if __name__ == "__main__":
    main() 