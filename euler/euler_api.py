#!/usr/bin/env python3
"""
API pour récupérer les données des positions Euler v2 de manière structurée
"""

from vault_info_client import EulerProductionClient, PRODUCTION_ADDRESS, parse_position_id
from typing import Dict, Any, List, Optional
import json

class EulerAPI:
    def __init__(self):
        self.client = EulerProductionClient()
    
    def get_production_positions(self, address: str = None) -> Dict[str, Any]:
        """
        Récupère les positions de l'adresse de production sous forme structurée
        
        Returns:
            {
                "address": "0x...",
                "success": True/False,
                "positions": {
                    "deposits": [
                        {
                            "position_id": "...",
                            "sub_account": "0x...",
                            "vault_address": "0x...",
                            "vault_info": {
                                "symbol": "...",
                                "name": "...",
                                "underlying_asset": {
                                    "symbol": "...",
                                    "name": "...",
                                    "decimals": 18
                                }
                            }
                        }
                    ],
                    "borrows": [...]
                },
                "summary": {
                    "total_positions": 4,
                    "total_deposits": 2,
                    "total_borrows": 2,
                    "unique_vaults": 3,
                    "vault_addresses": ["0x...", "0x..."]
                }
            }
        """
        if address is None:
            address = PRODUCTION_ADDRESS
        
        result = {
            "address": address,
            "success": False,
            "positions": {"deposits": [], "borrows": []},
            "summary": {
                "total_positions": 0,
                "total_deposits": 0,
                "total_borrows": 0,
                "unique_vaults": 0,
                "vault_addresses": []
            }
        }
        
        try:
            # 1. Récupérer les positions actives
            positions_data = self.client.query_active_positions(address)
            
            if not positions_data or not positions_data.get('trackingActiveAccount'):
                return result
            
            account = positions_data['trackingActiveAccount']
            deposits = account.get('deposits', [])
            borrows = account.get('borrows', [])
            
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
                vault_info = self.client.query_vault_info(vault_addr)
                if vault_info and vault_info.get('vault'):
                    vault_info_map[vault_addr] = vault_info['vault']
            
            # 4. Structurer les données des dépôts
            for deposit_id in deposits:
                sub_account, vault_addr = parse_position_id(deposit_id)
                vault_info = vault_info_map.get(vault_addr, {})
                
                deposit_data = {
                    "position_id": deposit_id,
                    "sub_account": sub_account,
                    "vault_address": vault_addr,
                    "vault_info": None
                }
                
                if vault_info:
                    asset = vault_info.get('asset', {})
                    deposit_data["vault_info"] = {
                        "symbol": vault_info.get('symbol'),
                        "name": vault_info.get('name'),
                        "underlying_asset": {
                            "symbol": asset.get('symbol'),
                            "name": asset.get('name'),
                            "decimals": asset.get('decimals')
                        },
                        "total_deposits": vault_info.get('totalDeposits'),
                        "total_borrows": vault_info.get('totalBorrows')
                    }
                
                result["positions"]["deposits"].append(deposit_data)
            
            # 5. Structurer les données des emprunts
            for borrow_id in borrows:
                sub_account, vault_addr = parse_position_id(borrow_id)
                vault_info = vault_info_map.get(vault_addr, {})
                
                borrow_data = {
                    "position_id": borrow_id,
                    "sub_account": sub_account,
                    "vault_address": vault_addr,
                    "vault_info": None
                }
                
                if vault_info:
                    asset = vault_info.get('asset', {})
                    borrow_data["vault_info"] = {
                        "symbol": vault_info.get('symbol'),
                        "name": vault_info.get('name'),
                        "underlying_asset": {
                            "symbol": asset.get('symbol'),
                            "name": asset.get('name'),
                            "decimals": asset.get('decimals')
                        },
                        "total_deposits": vault_info.get('totalDeposits'),
                        "total_borrows": vault_info.get('totalBorrows')
                    }
                
                result["positions"]["borrows"].append(borrow_data)
            
            # 6. Remplir le résumé
            result["summary"] = {
                "total_positions": len(deposits) + len(borrows),
                "total_deposits": len(deposits),
                "total_borrows": len(borrows),
                "unique_vaults": len(all_vault_addresses),
                "vault_addresses": list(all_vault_addresses)
            }
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_vault_summary(self, address: str = None) -> Dict[str, Any]:
        """
        Récupère un résumé des vaults utilisés par l'adresse
        
        Returns:
            {
                "address": "0x...",
                "vaults": [
                    {
                        "address": "0x...",
                        "symbol": "...",
                        "underlying_asset": "...",
                        "has_deposits": True,
                        "has_borrows": False
                    }
                ]
            }
        """
        positions_data = self.get_production_positions(address)
        
        if not positions_data["success"]:
            return {"address": address or PRODUCTION_ADDRESS, "vaults": []}
        
        vault_summary = {}
        
        # Analyser les dépôts
        for deposit in positions_data["positions"]["deposits"]:
            vault_addr = deposit["vault_address"]
            if vault_addr not in vault_summary:
                vault_summary[vault_addr] = {
                    "address": vault_addr,
                    "symbol": deposit["vault_info"]["symbol"] if deposit["vault_info"] else "N/A",
                    "underlying_asset": deposit["vault_info"]["underlying_asset"]["symbol"] if deposit["vault_info"] else "N/A",
                    "has_deposits": False,
                    "has_borrows": False
                }
            vault_summary[vault_addr]["has_deposits"] = True
        
        # Analyser les emprunts
        for borrow in positions_data["positions"]["borrows"]:
            vault_addr = borrow["vault_address"]
            if vault_addr not in vault_summary:
                vault_summary[vault_addr] = {
                    "address": vault_addr,
                    "symbol": borrow["vault_info"]["symbol"] if borrow["vault_info"] else "N/A",
                    "underlying_asset": borrow["vault_info"]["underlying_asset"]["symbol"] if borrow["vault_info"] else "N/A",
                    "has_deposits": False,
                    "has_borrows": False
                }
            vault_summary[vault_addr]["has_borrows"] = True
        
        return {
            "address": address or PRODUCTION_ADDRESS,
            "vaults": list(vault_summary.values())
        }

def main():
    """Test de l'API"""
    api = EulerAPI()
    
    print("🧪 Test de l'API Euler v2")
    print("=" * 40)
    
    # Test des positions
    positions = api.get_production_positions()
    print(f"✅ Récupération des positions: {'OK' if positions['success'] else 'ERREUR'}")
    
    if positions["success"]:
        print(f"📊 Résumé:")
        print(f"   - Total positions: {positions['summary']['total_positions']}")
        print(f"   - Dépôts: {positions['summary']['total_deposits']}")
        print(f"   - Emprunts: {positions['summary']['total_borrows']}")
        print(f"   - Vaults uniques: {positions['summary']['unique_vaults']}")
        
        # Afficher les vaults
        vault_summary = api.get_vault_summary()
        print(f"\n🏦 Vaults:")
        for vault in vault_summary["vaults"]:
            print(f"   • {vault['underlying_asset']} ({vault['symbol']})")
            print(f"     Address: {vault['address']}")
            print(f"     Deposits: {'✅' if vault['has_deposits'] else '❌'}")
            print(f"     Borrows: {'✅' if vault['has_borrows'] else '❌'}")
    
    # Optionnel: afficher le JSON complet
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        print(f"\n📄 Données JSON complètes:")
        print(json.dumps(positions, indent=2))

if __name__ == "__main__":
    import sys
    main() 