import os
import sys
import json
from web3 import Web3
from dotenv import load_dotenv
from decimal import Decimal

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.networks import RPC_URLS, NETWORK_TOKENS
from cowswap.cow_client import get_quote

# Load environment variables
load_dotenv()

# ERC20 ABI pour balanceOf + UNDERLYING_ASSET_ADDRESS
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "UNDERLYING_ASSET_ADDRESS", "outputs": [{"name": "", "type": "address"}], "type": "function"}
]

# Contrats par réseau
CONTRACTS_BY_NETWORK = {
    "base": [
        "0x90DA57E0A6C0d166Bf15764E03b83745Dc90025B",
        "0x38e59ADE183BbEb94583d44213c8f3297e9933e9",
        "0x067ae75628177FD257c2B1e500993e1a0baBcBd1",  # Aave Base GHO (aBasGHO)
        "0xcf3D55c10DB69f28fD1A75Bd73f3D8A2d9c595ad",  # Aave Base cbETH (aBascbETH)
        "0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7",  # Aave Base WETH (aBasWETH)
        "0x59dca05b6c26dbd64b5381374aAaC5CD05644C28",  # Aave Base Variable Debt USDC
        "0x99CBC45ea5bb7eF3a5BC08FB1B7E56bB2442Ef0D"   # Aave Base wstETH (aBaswstETH)
    ],
    "ethereum": [
        "0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8"   # aWETH Aave Ethereum WETH
    ]
}

# WETH addresses par réseau
WETH_ADDRESSES = {
    "base": "0x4200000000000000000000000000000000000006",
    "ethereum": "0xC02aaA39b223FE8d0A0e5C4F27eAD9083C756Cc2"
}

# Récupérer l'adresse de production depuis .env
PRODUCTION_ADDRESS = os.getenv('PRODUCTION_ADDRESS')

if not PRODUCTION_ADDRESS:
    print("PRODUCTION_ADDRESS non trouvé dans le fichier .env")
    print("Ajoutez PRODUCTION_ADDRESS=votre_adresse dans le fichier .env")
    sys.exit(1)

def get_underlying_decimals(w3, underlying_address):
    """Récupère les decimals de l'asset sous-jacent"""
    try:
        underlying_contract = w3.eth.contract(address=underlying_address, abi=ERC20_ABI)
        decimals = underlying_contract.functions.decimals().call()
        symbol = underlying_contract.functions.symbol().call()
        return decimals, symbol
    except:
        return None, None

def convert_to_weth(network, underlying_address, underlying_decimals, raw_balance):
    """Convertit un montant en WETH via cow_client"""
    try:
        weth_address = WETH_ADDRESSES[network]
        
        # Si c'est déjà WETH, pas besoin de conversion
        if underlying_address.lower() == weth_address.lower():
            return {
                "weth_value": raw_balance,
                "conversion_rate": "1.0",
                "conversion_source": "Direct WETH"
            }
        
        # Sinon, faire la conversion via cow_client
        result = get_quote(
            network=network,
            sell_token=underlying_address,
            buy_token=weth_address,
            amount=raw_balance,
            token_decimals=underlying_decimals,
            context="spot"
        )
        
        if result["quote"] and 'quote' in result["quote"]:
            weth_amount = result["quote"]["quote"]["buyAmount"]
            conversion_rate = result["conversion_details"]["rate"]
            conversion_source = result["conversion_details"]["source"]
            
            return {
                "weth_value": weth_amount,
                "conversion_rate": conversion_rate,
                "conversion_source": conversion_source
            }
        else:
            return {
                "weth_value": "0",
                "conversion_rate": "0",
                "conversion_source": "Failed"
            }
    except Exception as e:
        return {
            "weth_value": "0",
            "conversion_rate": "0",
            "conversion_source": f"Error: {str(e)[:50]}"
        }

def check_balance(w3, network, contract_address, wallet_address):
    """Vérifie la balance d'un contrat pour une adresse"""
    try:
        contract = w3.eth.contract(address=contract_address, abi=ERC20_ABI)
        balance_raw = contract.functions.balanceOf(wallet_address).call()
        decimals = contract.functions.decimals().call()
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        
        # Récupérer l'asset sous-jacent
        try:
            underlying_address = contract.functions.UNDERLYING_ASSET_ADDRESS().call()
            underlying_decimals, underlying_symbol = get_underlying_decimals(w3, underlying_address)
        except:
            underlying_address = "Unknown"
            underlying_decimals = None
            underlying_symbol = None
        
        # Convertir en WETH si nécessaire
        weth_conversion = None
        if underlying_address != "Unknown" and underlying_decimals is not None:
            weth_conversion = convert_to_weth(network, underlying_address, underlying_decimals, str(balance_raw))
        
        return {
            "symbol": symbol,
            "name": name,
            "decimals": decimals,
            "raw_balance": str(balance_raw),
            "underlying_asset": underlying_address,
            "underlying_decimals": underlying_decimals,
            "underlying_symbol": underlying_symbol,
            "weth_conversion": weth_conversion
        }
    except Exception as e:
        return None

def calculate_net_position(aave_data):
    """Calcule la position nette en WETH"""
    total_supply_weth = Decimal(0)
    total_debt_weth = Decimal(0)
    
    for position in aave_data:
        if position["weth_conversion"]:
            weth_value = Decimal(position["weth_conversion"]["weth_value"])
            
            # Si c'est un token de supply (commence par 'a')
            if position["symbol"].startswith("a"):
                total_supply_weth += weth_value
            # Si c'est un token de dette (contient 'Debt')
            elif "Debt" in position["symbol"]:
                total_debt_weth += weth_value
    
    # Position nette = Supply - Dette
    net_position = total_supply_weth - total_debt_weth
    
    return {
        "total_supply_weth": str(total_supply_weth),
        "total_debt_weth": str(total_debt_weth),
        "net_position_weth": str(net_position)
    }

def get_aave_balances_for_network(network):
    """Récupère les balances Aave pour un réseau spécifique"""
    rpc_url = RPC_URLS.get(network)
    if not rpc_url:
        return {"aave": [], "net_position": None}
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        return {"aave": [], "net_position": None}
    
    aave_data = []
    contracts = CONTRACTS_BY_NETWORK.get(network, [])
    
    for contract_address in contracts:
        result = check_balance(w3, network, contract_address, PRODUCTION_ADDRESS)
        
        if result and int(result["raw_balance"]) > 0:
            aave_data.append({
                "contract": contract_address,
                "symbol": result["symbol"],
                "raw_balance": result["raw_balance"],
                "decimals": result["decimals"],
                "underlying_asset": result["underlying_asset"],
                "underlying_decimals": result["underlying_decimals"],
                "underlying_symbol": result["underlying_symbol"],
                "weth_conversion": result["weth_conversion"]
            })
    
    # Calculer la position nette
    net_position = calculate_net_position(aave_data)
    
    return {
        "aave": aave_data,
        "net_position": net_position
    }

def get_aave_balances():
    """Récupère les balances Aave pour tous les réseaux et retourne un dictionnaire"""
    result = {}
    
    # Récupérer les données pour chaque réseau
    for network in CONTRACTS_BY_NETWORK.keys():
        network_data = get_aave_balances_for_network(network)
        result[network] = network_data
    
    return result

def main():
    result = get_aave_balances()
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 