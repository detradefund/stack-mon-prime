# Native Token Conversions (pufETH)

## Overview

Cette implémentation remplace les swaps CowSwap pour pufETH par sa fonction native :
- **pufETH** : utilise `convertToAssets()` du contrat Puffer
- **wstETH** : continue d'utiliser CowSwap (le code natif est disponible mais désactivé)

> **Note** : Le support natif pour wstETH est implémenté mais désactivé. Il peut être réactivé facilement en modifiant le code.

## Fonctionnalités

### Conversion Native (pufETH uniquement)
- **pufETH** : Utilise `pufETH.convertToAssets()` pour obtenir le montant ETH sous-jacent
- **wstETH** : Utilise CowSwap pour les prix du marché (code natif disponible mais désactivé)
- Pas de slippage ni de frais de trading pour pufETH
- Conversion instantanée sans dépendre des conditions de marché  
- Plus précis que les quotes AMM/DEX

### Configuration Interactive
- Au premier lancement, le système demande votre préférence pour pufETH :
  - **Mode NATIF** (recommandé) : Utilise `convertToAssets()` pour pufETH
  - **Mode COWSWAP** : Utilise les prix du marché via CoW Protocol pour tous
- wstETH utilise toujours CowSwap indépendamment du choix
- Intégration transparente dans le système existant

## Utilisation

### Via cow_client.get_quote() (Intégration Automatique)
```python
from cowswap.cow_client import get_quote

# Conversion wstETH → WETH (toujours CowSwap)
wsteth_result = get_quote(
    network="ethereum",
    sell_token="0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0",  # wstETH
    buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",   # WETH
    amount="1000000000000000000",  # 1 wstETH
    token_decimals=18,
    token_symbol="wstETH"
)
# Utilise CowSwap - pas de message spécial

# Conversion pufETH → WETH (mode natif si activé)
pufeth_result = get_quote(
    network="ethereum",
    sell_token="0xd9a442856c234a39a81a089c06451ebaa4306a72",  # pufETH
    buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",   # WETH
    amount="1000000000000000000",  # 1 pufETH
    token_decimals=18,
    token_symbol="pufETH"
)
# Output : "🔄 Detected pufETH → WETH conversion, using native convertToAssets() function"
```

### Directement via le module utils
```python
from utils.wsteth_converter import convert_wsteth_to_weth, convert_pufeth_to_weth

# Conversion wstETH
wsteth_result = convert_wsteth_to_weth("1000000000000000000", "ethereum")

# Conversion pufETH
pufeth_result = convert_pufeth_to_weth("1000000000000000000", "ethereum")
```

## Avantages

1. **Précision** : Utilise le taux de conversion exact du contrat Lido
2. **Fiabilité** : Pas de dépendance aux conditions de liquidité DEX
3. **Économie** : Aucun frais de trading ou slippage
4. **Performance** : Conversion instantanée sans attendre les quotes externes
5. **Transparence** : Taux de conversion transparent et vérifiable on-chain

## Exemples de Conversion

### pufETH (Mode Natif Activé)
Pour 1 pufETH au moment du test :
- **Input** : 1.000000 pufETH
- **Output** : 1.052377 WETH (taux : 1.052377 ETH/pufETH)
- **Source** : Puffer pufETH.convertToAssets()
- **Frais** : 0.0000%
- **Slippage** : 0.0000%

### wstETH (CowSwap)
Pour 1 wstETH :
- **Input** : 1.000000 wstETH
- **Output** : Variable selon les conditions de marché
- **Source** : CoW Protocol
- **Frais** : Variables selon le marché
- **Slippage** : Possible selon la liquidité

## Compatibilité

- ✅ Ethereum mainnet uniquement (pufETH et wstETH n'existent que sur mainnet)
- ✅ Compatible avec tous les balance managers existants
- ✅ Fallback automatique vers CowSwap en cas d'erreur
- ✅ Structure de réponse identique à CowSwap pour compatibilité

## Réactivation de wstETH Native

Le support natif pour wstETH est implémenté mais désactivé. Pour le réactiver :

1. Ouvrir le fichier `utils/wsteth_converter.py`
2. Dans la fonction `should_use_native_conversion()`, remplacer :
   ```python
   return is_pufeth(token_address, network)
   ```
   par :
   ```python
   return is_wsteth(token_address, network) or is_pufeth(token_address, network)
   ```
3. Mettre à jour le texte de configuration dans `_ask_user_preference()` si désiré

## Notes Techniques

- **pufETH** : Utilise `convertToAssets()` pour obtenir le montant ETH sous-jacent exact
- **wstETH** : Le code natif utilise `stEthPerToken()` (taux qui augmente avec les rewards)
- Les conversions natives assument que les tokens ≈ ETH ≈ WETH (généralement < 0.1% d'écart)
- La conversion pufETH reflète l'accumulation des rewards de staking Ethereum 