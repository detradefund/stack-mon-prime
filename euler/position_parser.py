#!/usr/bin/env python3
"""
Parser pour les IDs de position Euler v2
Extrait l'adresse du sub-account et l'adresse du vault depuis les IDs de position
"""

import sys
from query_active_positions import EulerGraphQLClient

def parse_position_id(entry: str) -> tuple:
    """
    Parse un ID de position Euler v2 pour extraire:
    - subAccount: l'adresse du sub-account (premiers 42 caractères)
    - vault: l'adresse du vault (40 caractères suivants avec 0x ajouté)
    
    Équivalent JavaScript:
    const vault = `0x${entry.substring(42)}`;
    const subAccount = entry.substring(0, 42);
    """
    if len(entry) < 82:  # 42 + 40 caractères minimum
        return None, None
    
    sub_account = entry[:42]  # Premiers 42 caractères (0x + 40 hex)
    vault = f"0x{entry[42:]}"  # 40 caractères suivants avec 0x ajouté
    
    return sub_account, vault

def analyze_positions(address: str):
    """
    Analyse les positions avec parsing des IDs
    """
    client = EulerGraphQLClient()
    
    print(f"🔍 Analyse des positions pour: {address}")
    print(f"📡 Endpoint: {client.endpoint}")
    print("-" * 80)
    
    result = client.query_active_positions(address)
    
    if not result or not result.get('trackingActiveAccount'):
        print("❌ Aucune position active trouvée")
        return
    
    account = result['trackingActiveAccount']
    deposits = account.get('deposits', [])
    borrows = account.get('borrows', [])
    
    print(f"✅ Positions trouvées pour: {account['mainAddress']}")
    print("=" * 80)
    
    # Analyser les dépôts
    print(f"\n💰 DÉPÔTS ({len(deposits)} positions):")
    if deposits:
        for i, deposit_id in enumerate(deposits, 1):
            sub_account, vault = parse_position_id(deposit_id)
            print(f"   {i}. Position ID: {deposit_id}")
            print(f"      👤 Sub-Account: {sub_account}")
            print(f"      🏦 Vault: {vault}")
            print(f"      📏 Longueur ID: {len(deposit_id)} caractères")
            print()
    else:
        print("   Aucun dépôt")
    
    # Analyser les emprunts
    print(f"\n🏦 EMPRUNTS ({len(borrows)} positions):")
    if borrows:
        for i, borrow_id in enumerate(borrows, 1):
            sub_account, vault = parse_position_id(borrow_id)
            print(f"   {i}. Position ID: {borrow_id}")
            print(f"      👤 Sub-Account: {sub_account}")
            print(f"      🏦 Vault: {vault}")
            print(f"      📏 Longueur ID: {len(borrow_id)} caractères")
            print()
    else:
        print("   Aucun emprunt")
    
    # Résumé avec vaults uniques
    all_positions = deposits + borrows
    vaults = set()
    sub_accounts = set()
    
    for pos_id in all_positions:
        sub_account, vault = parse_position_id(pos_id)
        if vault:
            vaults.add(vault)
        if sub_account:
            sub_accounts.add(sub_account)
    
    print(f"📊 RÉSUMÉ:")
    print(f"   - Total positions: {len(all_positions)}")
    print(f"   - Dépôts: {len(deposits)}")
    print(f"   - Emprunts: {len(borrows)}")
    print(f"   - Vaults uniques: {len(vaults)}")
    print(f"   - Sub-accounts uniques: {len(sub_accounts)}")
    
    if vaults:
        print(f"\n🏦 Vaults utilisés:")
        for vault in sorted(vaults):
            print(f"   - {vault}")
    
    if sub_accounts:
        print(f"\n👤 Sub-accounts:")
        for sub_account in sorted(sub_accounts):
            print(f"   - {sub_account}")

def test_parser():
    """
    Test la fonction de parsing avec un exemple
    """
    # Exemple d'ID de position depuis tes résultats
    example_id = "0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3d46bc453666ba11b4b08b0804e49a9d797546ee7d"
    
    print("🧪 Test du parser:")
    print(f"ID original: {example_id}")
    print(f"Longueur: {len(example_id)} caractères")
    
    sub_account, vault = parse_position_id(example_id)
    
    print(f"\nRésultat du parsing:")
    print(f"👤 Sub-Account: {sub_account}")
    print(f"🏦 Vault: {vault}")
    
    # Vérification des longueurs
    print(f"\nVérifications:")
    print(f"Sub-account longueur: {len(sub_account) if sub_account else 'N/A'} (attendu: 42)")
    print(f"Vault longueur: {len(vault) if vault else 'N/A'} (attendu: 42)")
    
    # Équivalent JavaScript pour comparaison
    print(f"\nÉquivalent JavaScript:")
    print(f"const vault = `0x${{entry.substring(42)}}`;  // {vault}")
    print(f"const subAccount = entry.substring(0, 42);    // {sub_account}")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_parser()
        else:
            analyze_positions(sys.argv[1])
    else:
        choice = input("Choisir:\n1. Tester le parser\n2. Analyser une adresse\nChoix (1 ou 2): ").strip()
        
        if choice == "1":
            test_parser()
        elif choice == "2":
            address = input("Entrez l'adresse Ethereum: ").strip()
            if address:
                analyze_positions(address)
            else:
                print("❌ Adresse requise")
        else:
            print("❌ Choix invalide")

if __name__ == "__main__":
    main() 