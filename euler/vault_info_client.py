#!/usr/bin/env python3
"""
Client Euler v2 avec récupération automatique des informations de vault
Utilise l'adresse de production par défaut et récupère symbol + underlying asset
"""

import requests
import json
from typing import Dict, Any, Optional, List
import sys

# Adresse de production par défaut
PRODUCTION_ADDRESS = "0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C"

def parse_position_id(entry: str) -> tuple:
    """Parse un ID de position pour extraire sub-account et vault"""
    if len(entry) < 82:
        return None, None
    
    sub_account = entry[:42]
    vault = f"0x{entry[42:]}"
    
    return sub_account, vault

class EulerProductionClient:
    def __init__(self):
        self.endpoint = "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-mainnet/latest/gn"
        self.headers = {"Content-Type": "application/json"}
        self.production_address = PRODUCTION_ADDRESS
    
    def query_active_positions(self, address: str = None) -> Optional[Dict[str, Any]]:
        """Requête pour les positions actives - utilise l'adresse de production par défaut"""
        if address is None:
            address = self.production_address
        
        query = """
        query Accounts($address: ID!) {
          trackingActiveAccount(id: $address) {
            mainAddress
            deposits
            borrows
          }
        }
        """
        
        return self._execute_query(query, {"address": address})
    
    def query_vault_info(self, vault_address: str) -> Optional[Dict[str, Any]]:
        """Requête pour récupérer les informations détaillées d'un vault"""
        query = """
        query VaultInfo($vaultAddress: ID!) {
          vault(id: $vaultAddress) {
            id
            name
            symbol
            asset {
              id
              symbol
              name
              decimals
            }
            totalShares
            totalBorrows
            totalDeposits
          }
        }
        """
        
        return self._execute_query(query, {"vaultAddress": vault_address})
    
    def query_multiple_vaults(self, vault_addresses: List[str]) -> Optional[Dict[str, Any]]:
        """Requête pour récupérer les informations de plusieurs vaults en une fois"""
        if not vault_addresses:
            return None
        
        # Construire la requête dynamiquement pour plusieurs vaults
        vault_queries = []
        for i, vault_addr in enumerate(vault_addresses):
            vault_queries.append(f'vault{i}: vault(id: "{vault_addr}") {{')
            vault_queries.append("""
                id
                name
                symbol
                asset {
                  id
                  symbol
                  name
                  decimals
                }
                totalShares
                totalBorrows
                totalDeposits
            }""")
        
        query = f"""
        query MultipleVaults {{
          {' '.join(vault_queries)}
        }}
        """
        
        return self._execute_query(query, {})
    
    def _execute_query(self, query: str, variables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Exécute une requête GraphQL"""
        payload = {"query": query, "variables": variables}
        
        try:
            response = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                print(f"❌ Erreurs GraphQL: {data['errors']}")
                return None
            
            return data.get("data")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur de requête: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Erreur de parsing JSON: {e}")
            return None
    
    def analyze_production_positions(self, address: str = None) -> None:
        """Analyse complète des positions avec informations détaillées des vaults"""
        if address is None:
            address = self.production_address
        
        print(f"🔍 Analyse des positions pour l'adresse de production: {address}")
        print(f"📡 Endpoint: {self.endpoint}")
        print("-" * 80)
        
        # 1. Récupérer les positions actives
        result = self.query_active_positions(address)
        
        if not result or not result.get('trackingActiveAccount'):
            print("❌ Aucune position active trouvée")
            return
        
        account = result['trackingActiveAccount']
        deposits = account.get('deposits', [])
        borrows = account.get('borrows', [])
        
        print(f"✅ Positions trouvées pour: {account['mainAddress']}")
        print("=" * 80)
        
        # 2. Extraire toutes les adresses de vault
        all_vault_addresses = set()
        
        for deposit_id in deposits:
            _, vault_addr = parse_position_id(deposit_id)
            if vault_addr:
                all_vault_addresses.add(vault_addr)
        
        for borrow_id in borrows:
            _, vault_addr = parse_position_id(borrow_id)
            if vault_addr:
                all_vault_addresses.add(vault_addr)
        
        # 3. Récupérer les informations de tous les vaults
        vault_info_map = {}
        
        for vault_addr in all_vault_addresses:
            vault_info = self.query_vault_info(vault_addr)
            if vault_info and vault_info.get('vault'):
                vault_info_map[vault_addr] = vault_info['vault']
            else:
                print(f"⚠️  Impossible de récupérer les informations pour le vault: {vault_addr}")
        
        # 4. Afficher les dépôts avec informations détaillées
        print(f"\n💰 DÉPÔTS ({len(deposits)} positions):")
        if deposits:
            for i, deposit_id in enumerate(deposits, 1):
                sub_account, vault_addr = parse_position_id(deposit_id)
                vault_info = vault_info_map.get(vault_addr, {})
                
                print(f"   {i}. Position ID: {deposit_id}")
                print(f"      👤 Sub-Account: {sub_account}")
                print(f"      🏦 Vault Address: {vault_addr}")
                
                if vault_info:
                    asset = vault_info.get('asset', {})
                    print(f"      📊 Vault Symbol: {vault_info.get('symbol', 'N/A')}")
                    print(f"      📛 Vault Name: {vault_info.get('name', 'N/A')}")
                    print(f"      🪙 Underlying Asset: {asset.get('symbol', 'N/A')} ({asset.get('name', 'N/A')})")
                    print(f"      🔢 Asset Decimals: {asset.get('decimals', 'N/A')}")
                    print(f"      📈 Total Deposits: {vault_info.get('totalDeposits', 'N/A')}")
                else:
                    print(f"      ⚠️  Informations du vault non disponibles")
                print()
        else:
            print("   Aucun dépôt")
        
        # 5. Afficher les emprunts avec informations détaillées
        print(f"\n🏦 EMPRUNTS ({len(borrows)} positions):")
        if borrows:
            for i, borrow_id in enumerate(borrows, 1):
                sub_account, vault_addr = parse_position_id(borrow_id)
                vault_info = vault_info_map.get(vault_addr, {})
                
                print(f"   {i}. Position ID: {borrow_id}")
                print(f"      👤 Sub-Account: {sub_account}")
                print(f"      🏦 Vault Address: {vault_addr}")
                
                if vault_info:
                    asset = vault_info.get('asset', {})
                    print(f"      📊 Vault Symbol: {vault_info.get('symbol', 'N/A')}")
                    print(f"      📛 Vault Name: {vault_info.get('name', 'N/A')}")
                    print(f"      🪙 Underlying Asset: {asset.get('symbol', 'N/A')} ({asset.get('name', 'N/A')})")
                    print(f"      🔢 Asset Decimals: {asset.get('decimals', 'N/A')}")
                    print(f"      📉 Total Borrows: {vault_info.get('totalBorrows', 'N/A')}")
                else:
                    print(f"      ⚠️  Informations du vault non disponibles")
                print()
        else:
            print("   Aucun emprunt")
        
        # 6. Résumé détaillé
        print(f"📊 RÉSUMÉ DÉTAILLÉ:")
        print(f"   - Adresse analysée: {address}")
        print(f"   - Total positions: {len(deposits) + len(borrows)}")
        print(f"   - Dépôts: {len(deposits)}")
        print(f"   - Emprunts: {len(borrows)}")
        print(f"   - Vaults uniques: {len(all_vault_addresses)}")
        
        if vault_info_map:
            print(f"\n🏦 DÉTAILS DES VAULTS:")
            for vault_addr, info in vault_info_map.items():
                asset = info.get('asset', {})
                print(f"   • {vault_addr}")
                print(f"     Symbol: {info.get('symbol', 'N/A')}")
                print(f"     Underlying: {asset.get('symbol', 'N/A')} ({asset.get('name', 'N/A')})")
                print(f"     Decimals: {asset.get('decimals', 'N/A')}")

def main():
    client = EulerProductionClient()
    
    # Utiliser l'adresse de production par défaut
    if len(sys.argv) > 1:
        address = sys.argv[1]
        print(f"📍 Utilisation de l'adresse personnalisée: {address}")
    else:
        address = PRODUCTION_ADDRESS
        print(f"📍 Utilisation de l'adresse de production: {address}")
    
    client.analyze_production_positions(address)

if __name__ == "__main__":
    main() 