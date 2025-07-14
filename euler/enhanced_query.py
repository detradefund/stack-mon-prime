#!/usr/bin/env python3
"""
Version améliorée du client GraphQL pour Euler v2 avec requêtes détaillées
"""

import requests
import json
from typing import Dict, Any, Optional, List

def parse_position_id(entry: str) -> tuple:
    """
    Parse un ID de position Euler v2 pour extraire:
    - subAccount: l'adresse du sub-account (premiers 42 caractères)
    - vault: l'adresse du vault (40 caractères suivants avec 0x ajouté)
    """
    if len(entry) < 82:  # 42 + 40 caractères minimum
        return None, None
    
    sub_account = entry[:42]  # Premiers 42 caractères (0x + 40 hex)
    vault = f"0x{entry[42:]}"  # 40 caractères suivants avec 0x ajouté
    
    return sub_account, vault

class EulerEnhancedClient:
    def __init__(self):
        self.endpoint = "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-mainnet/latest/gn"
        self.headers = {
            "Content-Type": "application/json",
        }
    
    def query_active_positions_detailed(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Requête détaillée pour les positions actives avec plus d'informations
        """
        query = """
        query DetailedAccounts($address: ID!) {
          trackingActiveAccount(id: $address) {
            mainAddress
            deposits {
              id
              vault {
                id
                name
                symbol
                asset {
                  id
                  symbol
                  name
                  decimals
                }
              }
              balance
              balanceFormatted
            }
            borrows {
              id
              vault {
                id
                name
                symbol
                asset {
                  id
                  symbol
                  name
                  decimals
                }
              }
              balance
              balanceFormatted
            }
          }
        }
        """
        
        variables = {"address": address}
        payload = {"query": query, "variables": variables}
        
        try:
            response = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                print(f"Erreurs GraphQL: {data['errors']}")
                return None
                
            return data.get("data")
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur de requête: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Erreur de parsing JSON: {e}")
            return None
    
    def query_basic_positions(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Requête basique pour les positions (comme dans l'exemple original)
        """
        query = """
        query Accounts($address: ID!) {
          trackingActiveAccount(id: $address) {
            mainAddress
            deposits
            borrows
          }
        }
        """
        
        variables = {"address": address}
        payload = {"query": query, "variables": variables}
        
        try:
            response = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                print(f"Erreurs GraphQL: {data['errors']}")
                return None
                
            return data.get("data")
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur de requête: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Erreur de parsing JSON: {e}")
            return None
    
    def format_detailed_positions(self, data: Dict[str, Any]) -> None:
        """
        Formatage détaillé des positions avec informations sur les tokens et parsing des IDs
        """
        if not data or not data.get("trackingActiveAccount"):
            print("❌ Aucune position active trouvée")
            return
        
        account = data["trackingActiveAccount"]
        
        print(f"📍 Adresse: {account['mainAddress']}")
        print("=" * 80)
        
        deposits = account.get('deposits', [])
        borrows = account.get('borrows', [])
        
        # Afficher les dépôts détaillés
        print(f"\n💰 DÉPÔTS ({len(deposits)} positions):")
        if deposits:
            for i, deposit in enumerate(deposits, 1):
                vault_info = deposit.get('vault', {})
                asset = vault_info.get('asset', {})
                position_id = deposit.get('id', 'N/A')
                
                # Parser l'ID de position
                sub_account, vault_address = parse_position_id(position_id)
                
                print(f"   {i}. {asset.get('symbol', 'N/A')} ({asset.get('name', 'N/A')})")
                print(f"      💳 Vault Symbol: {vault_info.get('symbol', 'N/A')}")
                print(f"      🏦 Vault Address: {vault_address if vault_address else 'N/A'}")
                print(f"      👤 Sub-Account: {sub_account if sub_account else 'N/A'}")
                print(f"      💵 Balance: {deposit.get('balanceFormatted', 'N/A')}")
                print(f"      🔢 Balance Raw: {deposit.get('balance', 'N/A')}")
                print(f"      📋 Position ID: {position_id}")
                print()
        else:
            print("   Aucun dépôt")
        
        # Afficher les emprunts détaillés
        print(f"\n🏦 EMPRUNTS ({len(borrows)} positions):")
        if borrows:
            for i, borrow in enumerate(borrows, 1):
                vault_info = borrow.get('vault', {})
                asset = vault_info.get('asset', {})
                position_id = borrow.get('id', 'N/A')
                
                # Parser l'ID de position
                sub_account, vault_address = parse_position_id(position_id)
                
                print(f"   {i}. {asset.get('symbol', 'N/A')} ({asset.get('name', 'N/A')})")
                print(f"      💳 Vault Symbol: {vault_info.get('symbol', 'N/A')}")
                print(f"      🏦 Vault Address: {vault_address if vault_address else 'N/A'}")
                print(f"      👤 Sub-Account: {sub_account if sub_account else 'N/A'}")
                print(f"      💵 Balance: {borrow.get('balanceFormatted', 'N/A')}")
                print(f"      🔢 Balance Raw: {borrow.get('balance', 'N/A')}")
                print(f"      📋 Position ID: {position_id}")
                print()
        else:
            print("   Aucun emprunt")
        
        # Résumé avec parsing des vaults et sub-accounts
        all_positions = []
        vault_addresses = set()
        sub_accounts = set()
        
        for deposit in deposits:
            position_id = deposit.get('id', '')
            all_positions.append(position_id)
            sub_account, vault_address = parse_position_id(position_id)
            if vault_address:
                vault_addresses.add(vault_address)
            if sub_account:
                sub_accounts.add(sub_account)
        
        for borrow in borrows:
            position_id = borrow.get('id', '')
            all_positions.append(position_id)
            sub_account, vault_address = parse_position_id(position_id)
            if vault_address:
                vault_addresses.add(vault_address)
            if sub_account:
                sub_accounts.add(sub_account)
        
        print(f"📊 RÉSUMÉ:")
        print(f"   - Total positions: {len(all_positions)}")
        print(f"   - Dépôts: {len(deposits)}")
        print(f"   - Emprunts: {len(borrows)}")
        print(f"   - Vaults uniques: {len(vault_addresses)}")
        print(f"   - Sub-accounts uniques: {len(sub_accounts)}")
        
        if vault_addresses:
            print(f"\n🏦 Vaults utilisés:")
            for vault_addr in sorted(vault_addresses):
                print(f"   - {vault_addr}")
        
        if sub_accounts:
            print(f"\n👤 Sub-accounts:")
            for sub_account in sorted(sub_accounts):
                print(f"   - {sub_account}")
        
        if len(deposits) > 0 or len(borrows) > 0:
            print(f"\n   - Statut: 🟢 Actif sur Euler v2")
        else:
            print(f"   - Statut: 🔴 Aucune position active")

def main():
    import sys
    
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        address = input("Entrez l'adresse Ethereum: ").strip()
    
    if not address:
        print("❌ Adresse requise")
        return
    
    client = EulerEnhancedClient()
    
    print(f"\n🔍 Interrogation détaillée pour: {address}")
    print(f"📡 Endpoint: {client.endpoint}")
    print("-" * 80)
    
    # Essayer d'abord la requête détaillée
    result = client.query_active_positions_detailed(address)
    
    if result:
        client.format_detailed_positions(result)
    else:
        print("⚠️  Requête détaillée échouée, tentative avec requête basique...")
        result = client.query_basic_positions(address)
        
        if result:
            # Utiliser le formatage simple pour les données basiques
            from query_active_positions import EulerGraphQLClient
            basic_client = EulerGraphQLClient()
            basic_client.format_position_data(result)
        else:
            print("❌ Toutes les requêtes ont échoué")

if __name__ == "__main__":
    main() 