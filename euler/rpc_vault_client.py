#!/usr/bin/env python3
"""
Client Euler v2 utilisant RPC Ethereum pour récupérer les informations des vaults
"""

import os
import requests
import json
import sys
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError
from decimal import Decimal

# Ajouter le répertoire parent au PYTHONPATH pour importer cow_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cowswap.cow_client import get_quote

# Charger les variables d'environnement depuis la racine du projet
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Adresse de production par défaut
PRODUCTION_ADDRESS = "0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C"

# Adresses des tokens pour les conversions
PUFETH_ADDRESS = "0xD9A442856C234a39a81a089C06451EBAa4306a72"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

# ABI minimal pour les vaults Euler v2
EULER_VAULT_ABI = [
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "asset",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalAssets",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },

    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "debtOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "shares", "type": "uint256"}],
        "name": "convertToAssets",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ABI minimal pour les tokens ERC20
ERC20_ABI = [
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def parse_position_id(entry: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse un ID de position pour extraire sub-account et vault"""
    if len(entry) < 82:
        return None, None
    
    sub_account = entry[:42]
    vault = f"0x{entry[42:]}"
    
    return sub_account, vault

class EulerRPCClient:
    def __init__(self):
        self.graphql_endpoint = "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-mainnet/latest/gn"
        self.headers = {"Content-Type": "application/json"}
        self.production_address = PRODUCTION_ADDRESS
        
        # Configurer Web3 avec RPC Ethereum
        ethereum_rpc = os.getenv('ETHEREUM_RPC')
        if not ethereum_rpc:
            raise ValueError("ETHEREUM_RPC non configuré dans les variables d'environnement")
        
        self.w3 = Web3(Web3.HTTPProvider(ethereum_rpc))
        if not self.w3.is_connected():
            raise ConnectionError(f"Impossible de se connecter au RPC Ethereum: {ethereum_rpc}")
        
        print(f"🌐 Connecté au RPC Ethereum: {ethereum_rpc[:50]}...")
    
    def query_active_positions(self, address: str = None) -> Optional[Dict[str, Any]]:
        """Récupère les positions actives via GraphQL"""
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
        
        payload = {"query": query, "variables": {"address": address}}
        
        try:
            response = requests.post(self.graphql_endpoint, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                print(f"❌ Erreurs GraphQL: {data['errors']}")
                return None
            
            return data.get("data")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur GraphQL: {e}")
            return None
    
    def get_vault_info_rpc(self, vault_address: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un vault via RPC"""
        try:
            # Créer le contrat vault
            vault_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(vault_address),
                abi=EULER_VAULT_ABI
            )
            
            # Récupérer les informations du vault
            vault_info = {
                "address": vault_address,
                "symbol": None,
                "name": None,
                "decimals": None,
                "total_supply": None,
                "total_assets": None,
                "underlying_asset": None
            }
            
            # Appels RPC pour récupérer les données du vault
            try:
                vault_info["symbol"] = vault_contract.functions.symbol().call()
            except Exception as e:
                print(f"⚠️  Erreur symbol() pour {vault_address}: {e}")
            
            try:
                vault_info["name"] = vault_contract.functions.name().call()
            except Exception as e:
                print(f"⚠️  Erreur name() pour {vault_address}: {e}")
            
            try:
                vault_info["decimals"] = vault_contract.functions.decimals().call()
            except Exception as e:
                print(f"⚠️  Erreur decimals() pour {vault_address}: {e}")
            
            try:
                vault_info["total_supply"] = vault_contract.functions.totalSupply().call()
            except Exception as e:
                print(f"⚠️  Erreur totalSupply() pour {vault_address}: {e}")
            
            try:
                vault_info["total_assets"] = vault_contract.functions.totalAssets().call()
            except Exception as e:
                print(f"⚠️  Erreur totalAssets() pour {vault_address}: {e}")
            
            # Récupérer l'adresse de l'underlying asset
            try:
                underlying_address = vault_contract.functions.asset().call()
                vault_info["underlying_asset"] = self.get_token_info_rpc(underlying_address)
                vault_info["underlying_asset_address"] = underlying_address  # Ajouter l'adresse brute
            except Exception as e:
                print(f"⚠️  Erreur asset() pour {vault_address}: {e}")
                vault_info["underlying_asset"] = None
                vault_info["underlying_asset_address"] = None
            
            return vault_info
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des infos du vault {vault_address}: {e}")
            return None
            
    def get_vault_balance_for_subaccount(self, vault_address: str, subaccount_address: str, position_type: str = "deposit") -> Optional[Dict[str, Any]]:
        """Récupère la balance d'un subaccount pour un vault spécifique"""
        try:
            # Créer le contrat vault
            vault_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(vault_address),
                abi=EULER_VAULT_ABI
            )
            
            # Récupérer les informations de base du vault
            vault_info = {
                "vault_address": vault_address,
                "subaccount_address": subaccount_address,
                "balance": None,
                "symbol": None,
                "name": None,
                "decimals": None,
                "underlying_asset_address": None,
                "underlying_asset_info": None
            }
            
            # Récupérer la balance du subaccount selon le type de position
            try:
                if position_type == "borrow":
                    # Pour les emprunts, utiliser debtOf
                    balance = vault_contract.functions.debtOf(Web3.to_checksum_address(subaccount_address)).call()
                    balance_type = "debt"
                else:
                    # Pour les dépôts, utiliser balanceOf
                    balance = vault_contract.functions.balanceOf(Web3.to_checksum_address(subaccount_address)).call()
                    balance_type = "shares"
                
                vault_info["balance"] = str(balance)
                vault_info["position_type"] = position_type
                vault_info["balance_type"] = balance_type
                
                if balance > 0:
                    if position_type == "borrow":
                        # Pour les emprunts, debtOf() donne déjà le montant en underlying token
                        print(f"✅ {position_type.capitalize()} pour {subaccount_address} dans {vault_address}: {balance} {balance_type} (already in underlying)")
                    else:
                        # Pour les dépôts, convertir les shares en underlying assets
                        try:
                            underlying_balance = vault_contract.functions.convertToAssets(balance).call()
                            vault_info["underlying_balance"] = str(underlying_balance)
                            print(f"✅ {position_type.capitalize()} pour {subaccount_address} dans {vault_address}: {balance} {balance_type} = {underlying_balance} underlying assets")
                        except Exception as e:
                            print(f"⚠️  Erreur convertToAssets() pour {balance} shares: {e}")
                            print(f"✅ {position_type.capitalize()} pour {subaccount_address} dans {vault_address}: {balance} {balance_type} (conversion failed)")
                else:
                    print(f"➖ {position_type.capitalize()} nul pour {subaccount_address} dans {vault_address}")
                    
            except Exception as e:
                print(f"⚠️  Erreur {position_type} pour {subaccount_address} dans {vault_address}: {e}")
                vault_info["balance"] = "0"
                vault_info["position_type"] = position_type
                vault_info["balance_type"] = "unknown"
            
            # Récupérer le symbol du vault
            try:
                vault_info["symbol"] = vault_contract.functions.symbol().call()
            except Exception as e:
                print(f"⚠️  Erreur symbol() pour {vault_address}: {e}")
            
            # Récupérer le nom du vault
            try:
                vault_info["name"] = vault_contract.functions.name().call()
            except Exception as e:
                print(f"⚠️  Erreur name() pour {vault_address}: {e}")
            
            # Récupérer les decimals du vault
            try:
                vault_info["decimals"] = vault_contract.functions.decimals().call()
            except Exception as e:
                print(f"⚠️  Erreur decimals() pour {vault_address}: {e}")
            
            # Récupérer l'adresse de l'underlying asset
            try:
                underlying_address = vault_contract.functions.asset().call()
                vault_info["underlying_asset_address"] = underlying_address
                vault_info["underlying_asset_info"] = self.get_token_info_rpc(underlying_address)
                print(f"✅ Underlying asset pour {vault_address}: {underlying_address}")
            except Exception as e:
                print(f"⚠️  Erreur asset() pour {vault_address}: {e}")
                vault_info["underlying_asset_address"] = None
                vault_info["underlying_asset_info"] = None
            
            return vault_info
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération de la balance du vault {vault_address} pour {subaccount_address}: {e}")
            return None
    
    def get_token_info_rpc(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un token ERC20 via RPC"""
        try:
            # Créer le contrat token
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            token_info = {
                "address": token_address,
                "symbol": None,
                "name": None,
                "decimals": None
            }
            
            # Appels RPC pour récupérer les données du token
            try:
                token_info["symbol"] = token_contract.functions.symbol().call()
            except Exception as e:
                print(f"⚠️  Erreur symbol() pour token {token_address}: {e}")
            
            try:
                token_info["name"] = token_contract.functions.name().call()
            except Exception as e:
                print(f"⚠️  Erreur name() pour token {token_address}: {e}")
            
            try:
                token_info["decimals"] = token_contract.functions.decimals().call()
            except Exception as e:
                print(f"⚠️  Erreur decimals() pour token {token_address}: {e}")
            
            return token_info
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des infos du token {token_address}: {e}")
            return None
    
    def get_all_vault_balances_for_positions(self, address: str = None) -> Dict[str, Any]:
        """Récupère toutes les balances des vaults pour les positions actives, regroupées par subaccount"""
        if address is None:
            address = self.production_address
        
        print(f"🔍 Récupération des balances des vaults pour: {address}")
        print("-" * 80)
        
        # 1. Récupérer les positions actives via GraphQL
        result = self.query_active_positions(address)
        
        if not result or not result.get('trackingActiveAccount'):
            print("❌ Aucune position active trouvée")
            return {"success": False, "error": "Aucune position active"}
        
        account = result['trackingActiveAccount']
        deposits = account.get('deposits', [])
        borrows = account.get('borrows', [])
        
        print(f"✅ Positions trouvées pour: {account['mainAddress']}")
        
        # 2. Regrouper par subaccount
        subaccounts = {}
        
        # Analyser les dépôts
        for deposit_id in deposits:
            sub_account, vault_addr = parse_position_id(deposit_id)
            if sub_account and vault_addr:
                print(f"\n💰 Analyse du dépôt: {sub_account} -> {vault_addr}")
                balance_info = self.get_vault_balance_for_subaccount(vault_addr, sub_account, "deposit")
                
                if balance_info:
                    # Initialiser le subaccount si nécessaire
                    if sub_account not in subaccounts:
                        subaccounts[sub_account] = {
                            "subaccount_address": sub_account,
                            "positions": {
                                "deposits": [],
                                "borrows": []
                            }
                        }
                    
                    # Ajouter la position de dépôt
                    deposit_position = {
                        "position_id": deposit_id,
                        "vault_address": vault_addr,
                        "symbol": balance_info.get("symbol"),
                        "name": balance_info.get("name"),
                        "decimals": balance_info.get("decimals"),
                        "balance": balance_info.get("balance"),
                        "underlying_balance": balance_info.get("underlying_balance"),
                        "position_type": balance_info.get("position_type"),
                        "balance_type": balance_info.get("balance_type"),
                        "underlying_asset_address": balance_info.get("underlying_asset_address"),
                        "underlying_asset_info": balance_info.get("underlying_asset_info")
                    }
                    subaccounts[sub_account]["positions"]["deposits"].append(deposit_position)
        
        # Analyser les emprunts
        for borrow_id in borrows:
            sub_account, vault_addr = parse_position_id(borrow_id)
            if sub_account and vault_addr:
                print(f"\n💸 Analyse de l'emprunt: {sub_account} -> {vault_addr}")
                balance_info = self.get_vault_balance_for_subaccount(vault_addr, sub_account, "borrow")
                
                if balance_info:
                    # Initialiser le subaccount si nécessaire
                    if sub_account not in subaccounts:
                        subaccounts[sub_account] = {
                            "subaccount_address": sub_account,
                            "positions": {
                                "deposits": [],
                                "borrows": []
                            }
                        }
                    
                    # Ajouter la position d'emprunt
                    borrow_position = {
                        "position_id": borrow_id,
                        "vault_address": vault_addr,
                        "symbol": balance_info.get("symbol"),
                        "name": balance_info.get("name"),
                        "decimals": balance_info.get("decimals"),
                        "balance": balance_info.get("balance"),
                        "position_type": balance_info.get("position_type"),
                        "balance_type": balance_info.get("balance_type"),
                        "underlying_asset_address": balance_info.get("underlying_asset_address"),
                        "underlying_asset_info": balance_info.get("underlying_asset_info")
                    }
                    subaccounts[sub_account]["positions"]["borrows"].append(borrow_position)
        
        # 3. Calculer les statistiques
        total_deposits = sum(len(sub["positions"]["deposits"]) for sub in subaccounts.values())
        total_borrows = sum(len(sub["positions"]["borrows"]) for sub in subaccounts.values())
        total_positions = total_deposits + total_borrows
        
        # Compter les balances non-nulles
        non_zero_positions = 0
        for subaccount_data in subaccounts.values():
            for deposit in subaccount_data["positions"]["deposits"]:
                if deposit.get("balance") != "0":
                    non_zero_positions += 1
            for borrow in subaccount_data["positions"]["borrows"]:
                if borrow.get("balance") != "0":
                    non_zero_positions += 1
        
        # 4. Affichage du résumé
        print(f"\n📊 Résumé des balances par subaccount:")
        print(f"   - Subaccounts trouvés: {len(subaccounts)}")
        print(f"   - Total positions: {total_positions}")
        print(f"   - Dépôts: {total_deposits}")
        print(f"   - Emprunts: {total_borrows}")
        print(f"   - Positions avec balance non-nulle: {non_zero_positions}")
        
        # Afficher les détails par subaccount
        for subaccount_addr, subaccount_data in subaccounts.items():
            print(f"\n👤 Subaccount: {subaccount_addr}")
            
            # Dépôts
            deposits_with_balance = [d for d in subaccount_data["positions"]["deposits"] if d.get("balance") != "0"]
            if deposits_with_balance:
                print(f"   💰 Dépôts ({len(deposits_with_balance)}):")
                for deposit in deposits_with_balance:
                    symbol = deposit.get("symbol", "Unknown")
                    balance_type = deposit.get("balance_type", "shares")
                    underlying_balance = deposit.get("underlying_balance")
                    underlying_symbol = deposit.get("underlying_asset_info", {}).get("symbol", "Unknown")
                    if underlying_balance:
                        print(f"      - {symbol}: {deposit['balance']} {balance_type} = {underlying_balance} {underlying_symbol}")
                    else:
                        print(f"      - {symbol}: {deposit['balance']} {balance_type}")
            
            # Emprunts
            borrows_with_balance = [b for b in subaccount_data["positions"]["borrows"] if b.get("balance") != "0"]
            if borrows_with_balance:
                print(f"   💸 Emprunts ({len(borrows_with_balance)}):")
                for borrow in borrows_with_balance:
                    symbol = borrow.get("symbol", "Unknown")
                    balance_type = borrow.get("balance_type", "debt")
                    underlying_symbol = borrow.get("underlying_asset_info", {}).get("symbol", "Unknown")
                    print(f"      - {symbol}: {borrow['balance']} {balance_type} ({underlying_symbol})")
        
        return {
            "success": True,
            "address": address,
            "subaccounts": subaccounts,
            "summary": {
                "total_subaccounts": len(subaccounts),
                "total_positions": total_positions,
                "total_deposits": total_deposits,
                "total_borrows": total_borrows,
                "non_zero_positions": non_zero_positions
            }
        }
    
    def get_balances(self, address: str = None) -> Dict[str, Any]:
        """Récupère les balances Euler et calcule le net par position (format aggregator)"""
        if address is None:
            address = self.production_address
        
        print("\n" + "="*80)
        print("EULER BALANCE MANAGER")
        print("="*80)
        
        # 1. Récupérer les balances des vaults
        balance_result = self.get_all_vault_balances_for_positions(address)
        
        if not balance_result['success']:
            print(f"❌ Erreur lors de la récupération des balances: {balance_result.get('error')}")
            return {"euler": {"ethereum": {}}}
        
        subaccounts = balance_result['subaccounts']
        if not subaccounts:
            print("❌ Aucun subaccount trouvé")
            return {"euler": {"ethereum": {}}}
        
        # 2. Calculer le net par subaccount
        net_positions = {}
        deposits_breakdown = {}
        borrows_breakdown = {}
        total_net_weth = Decimal('0')
        
        for subaccount_addr, subaccount_data in subaccounts.items():
            print(f"\n🔄 Calcul du net pour subaccount: {subaccount_addr}")
            
            # Initialiser les totaux
            total_deposits_weth = Decimal('0')
            total_borrows_weth = Decimal('0')
            
            # Traiter les dépôts
            deposits = subaccount_data['positions']['deposits']
            for deposit in deposits:
                if deposit.get('balance') != '0':
                    underlying_balance = deposit.get('underlying_balance')
                    underlying_asset_address = deposit.get('underlying_asset_address')
                    symbol = deposit.get('symbol', 'Unknown')
                    
                    if underlying_balance and underlying_asset_address:
                        # Convertir en WETH si ce n'est pas déjà du WETH
                        if underlying_asset_address.lower() == WETH_ADDRESS.lower():
                            # Déjà du WETH, pas besoin de conversion
                            deposit_weth = Decimal(underlying_balance)
                            conversion_details = {
                                "source": "Direct",
                                "price_impact": "0.0000%",
                                "rate": "1.000000",
                                "fee_percentage": "0.0000%",
                                "fallback": False,
                                "note": "Direct 1:1 conversion"
                            }
                            print(f"   💰 {symbol}: {underlying_balance} WETH (déjà en WETH)")
                        elif underlying_asset_address.lower() == PUFETH_ADDRESS.lower():
                            # Convertir pufETH en WETH via CoW
                            conversion_result = self._convert_pufeth_to_weth_with_details(underlying_balance)
                            deposit_weth = conversion_result['weth_amount']
                            conversion_details = conversion_result['conversion_details']
                            print(f"   💰 {symbol}: {underlying_balance} pufETH = {deposit_weth} WETH")
                        else:
                            # Autre token, pas de conversion implémentée
                            print(f"   ⚠️  {symbol}: Conversion non implémentée pour {underlying_asset_address}")
                            deposit_weth = Decimal('0')
                            conversion_details = {
                                "source": "Failed",
                                "price_impact": "N/A",
                                "rate": "0",
                                "fee_percentage": "N/A",
                                "fallback": False,
                                "note": "Conversion not implemented"
                            }
                        
                        total_deposits_weth += deposit_weth
                        
                        # Stocker les détails du dépôt
                        if symbol not in deposits_breakdown:
                            deposits_breakdown[symbol] = {
                                "amount": underlying_balance,
                                "decimals": 18,
                                "value": {
                                    "WETH": {
                                        "amount": int(deposit_weth),
                                        "decimals": 18,
                                        "conversion_details": conversion_details
                                    }
                                }
                            }
                        else:
                            # Additionner si plusieurs positions du même token
                            existing_weth = deposits_breakdown[symbol]["value"]["WETH"]["amount"]
                            deposits_breakdown[symbol]["value"]["WETH"]["amount"] = existing_weth + int(deposit_weth)
            
            # Traiter les emprunts
            borrows = subaccount_data['positions']['borrows']
            for borrow in borrows:
                if borrow.get('balance') != '0':
                    balance = borrow.get('balance')
                    underlying_asset_address = borrow.get('underlying_asset_address')
                    symbol = borrow.get('symbol', 'Unknown')
                    
                    if balance and underlying_asset_address:
                        # Les emprunts sont déjà en underlying token
                        if underlying_asset_address.lower() == WETH_ADDRESS.lower():
                            # Déjà du WETH
                            borrow_weth = Decimal(balance)
                            print(f"   💸 {symbol}: {balance} WETH (déjà en WETH)")
                            
                            # Stocker les détails de l'emprunt
                            if symbol not in borrows_breakdown:
                                borrows_breakdown[symbol] = {
                                    "amount": balance,
                                    "decimals": 18,
                                    "value": {
                                        "WETH": {
                                            "amount": int(borrow_weth),
                                            "decimals": 18,
                                            "conversion_details": {
                                                "source": "Direct",
                                                "price_impact": "0.0000%",
                                                "rate": "1.000000",
                                                "fee_percentage": "0.0000%",
                                                "fallback": False,
                                                "note": "Direct 1:1 conversion (debt)"
                                            }
                                        }
                                    }
                                }
                            else:
                                # Additionner si plusieurs positions du même token
                                existing_weth = borrows_breakdown[symbol]["value"]["WETH"]["amount"]
                                borrows_breakdown[symbol]["value"]["WETH"]["amount"] = existing_weth + int(borrow_weth)
                        else:
                            # Autre token, pas de conversion implémentée
                            print(f"   ⚠️  {symbol}: Conversion non implémentée pour {underlying_asset_address}")
                            borrow_weth = Decimal('0')
                        
                        total_borrows_weth += borrow_weth
            
            # Calculer le net
            net_weth = total_deposits_weth - total_borrows_weth
            total_net_weth += net_weth
            
            # Stocker les résultats
            net_positions[subaccount_addr] = {
                'deposits_weth': str(total_deposits_weth),
                'borrows_weth': str(total_borrows_weth),
                'net_weth': str(net_weth),
                'net_eth': str(net_weth / Decimal(10**18))  # Conversion en ETH lisible
            }
            
            print(f"   📊 Résumé:")
            print(f"      - Dépôts totaux: {total_deposits_weth / Decimal(10**18):.6f} ETH")
            print(f"      - Emprunts totaux: {total_borrows_weth / Decimal(10**18):.6f} ETH")
            print(f"      - Net: {net_weth / Decimal(10**18):.6f} ETH")
        
        print(f"\n🎯 RÉSUMÉ GLOBAL:")
        print(f"   - Nombre de subaccounts: {len(net_positions)}")
        print(f"   - Net total: {total_net_weth / Decimal(10**18):.6f} ETH")
        
        # 3. Construire le résultat au format aggregator
        result = {
            "euler": {
                "ethereum": {
                    "net_position": {
                        "amount": str(int(total_net_weth)),
                        "decimals": 18,
                        "deposits": deposits_breakdown,
                        "borrows": borrows_breakdown,
                        "subaccounts": net_positions,
                        "totals": {
                            "wei": int(total_net_weth),
                            "formatted": f"{total_net_weth / Decimal(10**18):.6f}"
                        }
                    }
                }
            }
        }
        
        # Ajouter le total au niveau du réseau
        if int(total_net_weth) != 0:
            result["euler"]["ethereum"]["totals"] = {
                "wei": int(total_net_weth),
                "formatted": f"{total_net_weth / Decimal(10**18):.6f}"
            }
        
        # Ajouter le total au niveau du protocole
        if int(total_net_weth) != 0:
            result["euler"]["totals"] = {
                "wei": int(total_net_weth),
                "formatted": f"{total_net_weth / Decimal(10**18):.6f}"
            }
        
        return result
    
    def _convert_pufeth_to_weth(self, pufeth_amount: str) -> Decimal:
        """Convertit un montant de pufETH en WETH via CoW Protocol"""
        result = self._convert_pufeth_to_weth_with_details(pufeth_amount)
        return result['weth_amount']
    
    def _convert_pufeth_to_weth_with_details(self, pufeth_amount: str) -> Dict[str, Any]:
        """Convertit un montant de pufETH en WETH avec détails de conversion"""
        try:
            print(f"      🔄 Conversion de {pufeth_amount} pufETH en WETH...")
            
            # Utiliser cow_client pour obtenir le quote
            quote_result = get_quote(
                network="ethereum",
                sell_token=PUFETH_ADDRESS,
                buy_token=WETH_ADDRESS,
                amount=pufeth_amount,
                token_decimals=18,  # pufETH a 18 decimales
                token_symbol="pufETH"
            )
            
            if quote_result.get('quote') and quote_result['quote'].get('quote'):
                buy_amount = quote_result['quote']['quote']['buyAmount']
                conversion_details = quote_result.get('conversion_details', {})
                
                print(f"      ✅ Conversion réussie via {conversion_details.get('source', 'CoW')}")
                print(f"      📈 Taux: {conversion_details.get('rate', 'N/A')}")
                
                return {
                    'weth_amount': Decimal(buy_amount),
                    'conversion_details': conversion_details
                }
            else:
                print(f"      ❌ Erreur lors de la conversion: {quote_result}")
                return {
                    'weth_amount': Decimal('0'),
                    'conversion_details': {
                        "source": "Failed",
                        "price_impact": "N/A",
                        "rate": "0",
                        "fee_percentage": "N/A",
                        "fallback": True,
                        "note": "Quote failed"
                    }
                }
                
        except Exception as e:
            print(f"      ❌ Erreur lors de la conversion pufETH->WETH: {e}")
            return {
                'weth_amount': Decimal('0'),
                'conversion_details': {
                    "source": "Error",
                    "price_impact": "N/A",
                    "rate": "0",
                    "fee_percentage": "N/A",
                    "fallback": True,
                    "note": f"Error: {str(e)}"
                }
            }
    
    def analyze_production_positions_rpc(self, address: str = None) -> Dict[str, Any]:
        """Analyse complète des positions avec informations RPC"""
        if address is None:
            address = self.production_address
        
        print(f"🔍 Analyse des positions Euler v2 (RPC): {address}")
        print(f"📡 GraphQL: {self.graphql_endpoint}")
        print(f"🌐 Ethereum RPC: {os.getenv('ETHEREUM_RPC', '')[:50]}...")
        print("-" * 80)
        
        # 1. Récupérer les positions actives via GraphQL
        result = self.query_active_positions(address)
        
        if not result or not result.get('trackingActiveAccount'):
            print("❌ Aucune position active trouvée")
            return {"success": False, "error": "Aucune position active"}
        
        account = result['trackingActiveAccount']
        deposits = account.get('deposits', [])
        borrows = account.get('borrows', [])
        
        print(f"✅ Positions trouvées pour: {account['mainAddress']}")
        print("=" * 80)
        
        # 2. Analyser toutes les positions et récupérer les infos des vaults
        vault_info_cache = {}
        
        def get_vault_info_cached(vault_addr):
            if vault_addr not in vault_info_cache:
                print(f"🔄 Récupération des infos du vault: {vault_addr}")
                vault_info_cache[vault_addr] = self.get_vault_info_rpc(vault_addr)
            return vault_info_cache[vault_addr]
        
        # 3. Regrouper les positions par sub-account
        positions_by_subaccount = {}
        
        # Regrouper les dépôts par sub-account
        for deposit_id in deposits:
            sub_account, vault_addr = parse_position_id(deposit_id)
            if sub_account not in positions_by_subaccount:
                positions_by_subaccount[sub_account] = {
                    'sub_account': sub_account,
                    'deposits': [],
                    'borrows': []
                }
            positions_by_subaccount[sub_account]['deposits'].append({
                'id': deposit_id,
                'vault_address': vault_addr
            })
        
        # Regrouper les emprunts par sub-account
        for borrow_id in borrows:
            sub_account, vault_addr = parse_position_id(borrow_id)
            if sub_account not in positions_by_subaccount:
                positions_by_subaccount[sub_account] = {
                    'sub_account': sub_account,
                    'deposits': [],
                    'borrows': []
                }
            positions_by_subaccount[sub_account]['borrows'].append({
                'id': borrow_id,
                'vault_address': vault_addr
            })
        
        # 4. Afficher chaque position (regroupée par sub-account)
        print(f"\n📋 POSITIONS ACTIVES ({len(positions_by_subaccount)} positions):")
        
        if positions_by_subaccount:
            for i, (sub_account, position_data) in enumerate(positions_by_subaccount.items(), 1):
                print(f"\n{i}. 📊 POSITION - Sub-Account: {sub_account}")
                print(f"   {'='*60}")
                
                # Afficher les dépôts de cette position
                position_deposits = position_data['deposits']
                if position_deposits:
                    print(f"   💰 DÉPÔTS ({len(position_deposits)}):")
                    for j, deposit in enumerate(position_deposits, 1):
                        vault_info = get_vault_info_cached(deposit['vault_address'])
                        print(f"      {j}. Vault: {deposit['vault_address']}")
                        if vault_info:
                            print(f"         📊 Symbol: {vault_info.get('symbol', 'N/A')}")
                            print(f"         📛 Name: {vault_info.get('name', 'N/A')}")
                            underlying = vault_info.get('underlying_asset')
                            if underlying:
                                print(f"         🪙 Underlying: {underlying.get('symbol', 'N/A')} ({underlying.get('name', 'N/A')})")
                        print(f"         📋 Position ID: {deposit['id']}")
                        print()
                else:
                    print(f"   💰 DÉPÔTS: Aucun")
                
                # Afficher les emprunts de cette position
                position_borrows = position_data['borrows']
                if position_borrows:
                    print(f"   🏦 EMPRUNTS ({len(position_borrows)}):")
                    for j, borrow in enumerate(position_borrows, 1):
                        vault_info = get_vault_info_cached(borrow['vault_address'])
                        print(f"      {j}. Vault: {borrow['vault_address']}")
                        if vault_info:
                            print(f"         📊 Symbol: {vault_info.get('symbol', 'N/A')}")
                            print(f"         📛 Name: {vault_info.get('name', 'N/A')}")
                            underlying = vault_info.get('underlying_asset')
                            if underlying:
                                print(f"         🪙 Underlying: {underlying.get('symbol', 'N/A')} ({underlying.get('name', 'N/A')})")
                        print(f"         📋 Position ID: {borrow['id']}")
                        print()
                else:
                    print(f"   🏦 EMPRUNTS: Aucun")
        else:
            print("   Aucune position active")
        
        # 5. Résumé
        unique_vaults = set()
        total_deposits = 0
        total_borrows = 0
        
        for sub_account, position_data in positions_by_subaccount.items():
            total_deposits += len(position_data['deposits'])
            total_borrows += len(position_data['borrows'])
            
            for deposit in position_data['deposits']:
                unique_vaults.add(deposit['vault_address'])
            for borrow in position_data['borrows']:
                unique_vaults.add(borrow['vault_address'])
        
        print(f"\n📊 RÉSUMÉ DÉTAILLÉ:")
        print(f"   - Adresse analysée: {address}")
        print(f"   - Positions (sub-accounts): {len(positions_by_subaccount)}")
        print(f"   - Total dépôts: {total_deposits}")
        print(f"   - Total emprunts: {total_borrows}")
        print(f"   - Vaults uniques: {len(unique_vaults)}")
        
        if vault_info_cache:
            print(f"\n🏦 RÉSUMÉ DES VAULTS:")
            for vault_addr, info in vault_info_cache.items():
                if info:
                    underlying = info.get('underlying_asset', {})
                    print(f"   • {vault_addr}")
                    print(f"     Vault: {info.get('symbol', 'N/A')} ({info.get('name', 'N/A')})")
                    print(f"     Underlying: {underlying.get('symbol', 'N/A')} ({underlying.get('name', 'N/A')})")
        
        return {
            "success": True,
            "address": address,
            "positions": {"deposits": deposits, "borrows": borrows},
            "positions_by_subaccount": positions_by_subaccount,
            "vault_info": vault_info_cache
        }

def main():
    import sys
    
    try:
        client = EulerRPCClient()
        
        # Utiliser l'adresse de production par défaut
        if len(sys.argv) > 1:
            address = sys.argv[1]
            print(f"📍 Utilisation de l'adresse personnalisée: {address}")
        else:
            address = PRODUCTION_ADDRESS
            print(f"📍 Utilisation de l'adresse de production: {address}")
        
        client.analyze_production_positions_rpc(address)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 