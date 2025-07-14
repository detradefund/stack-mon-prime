# Euler v2 GraphQL Client

Ce dossier contient un client Python pour interroger le subgraph Euler v2 mainnet hébergé par Goldsky.

## Endpoint

```
https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-mainnet/latest/gn
```

## Configuration

### Fichier .env (Requis pour les scripts RPC)

Créez ou mettez à jour le fichier `.env` à la racine du projet avec :

```bash
# Configuration RPC Ethereum
ETHEREUM_RPC=https://your-ethereum-rpc-endpoint.com

# Exemple avec Alchemy
ETHEREUM_RPC=https://eth-mainnet.g.alchemy.com/v2/your-api-key

# Exemple avec Infura
ETHEREUM_RPC=https://mainnet.infura.io/v3/your-project-id
```

## Fichiers

- `query_active_positions.py`: Classe principale du client GraphQL
- `query_direct.py`: Script direct pour faire des requêtes sans options
- `position_parser.py`: Analyseur d'IDs de position avec parsing détaillé
- `enhanced_query.py`: Version améliorée avec requêtes détaillées
- `rpc_vault_client.py`: **Client RPC complet** pour récupérer les informations des vaults
- `rpc_simple.py`: **Version simplifiée du client RPC** (recommandée)
- `vault_info_client.py`: Client avec requêtes GraphQL pour vaults (obsolète)
- `production_analysis.py`: Script simple pour analyse de production
- `euler_api.py`: API structurée pour récupérer les données
- `test_query.py`: Script de test pour démonstration
- `README.md`: Cette documentation

## Utilisation

### ⭐ Script RPC avec informations complètes (Recommandé)

```bash
# Utilise l'adresse de production et ETHEREUM_RPC du fichier .env
python euler/production_rpc.py

# Ou version simplifiée
python euler/rpc_simple.py
```

**⚠️ Important**: Ces scripts nécessitent `ETHEREUM_RPC` configuré dans le fichier `.env` à la racine du projet.

### Scripts GraphQL (Plus basiques)

```bash
# Script direct avec adresse en paramètre
python euler/query_direct.py 0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C

# Analyseur de positions avec parsing des IDs
python euler/position_parser.py 0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C

# Version améliorée
python euler/enhanced_query.py 0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C
```

### Utilisation Programmée

```python
from euler.query_active_positions import EulerGraphQLClient

client = EulerGraphQLClient()
result = client.query_active_positions("0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C")

if result:
    client.format_position_data(result)
```

## Parsing des IDs de Position

Les IDs de position retournés par l'API sont des concaténations de :
- **Premiers 42 caractères** : Adresse du sub-account (0x + 40 hex)
- **40 caractères suivants** : Adresse du vault (sans 0x)

### Exemple de Parsing

```python
from euler.position_parser import parse_position_id

position_id = "0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3d46bc453666ba11b4b08b0804e49a9d797546ee7d"
sub_account, vault = parse_position_id(position_id)

print(f"Sub-Account: {sub_account}")  # 0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3c
print(f"Vault: {vault}")              # 0x46bc453666ba11b4b08b0804e49a9d797546ee7d
```

### Équivalent JavaScript

```javascript
const vault = `0x${entry.substring(42)}`;
const subAccount = entry.substring(0, 42);
```

## Requêtes GraphQL

### Requête Basique

```graphql
query Accounts($address: ID!) {
  trackingActiveAccount(id: $address) {
    mainAddress
    deposits
    borrows
  }
}
```

### Requête Détaillée

```graphql
query DetailedAccounts($address: ID!) {
  trackingActiveAccount(id: $address) {
    mainAddress
    deposits {
      id
      vault {
        id
        symbol
        asset {
          symbol
          name
        }
      }
      balance
      balanceFormatted
    }
    borrows {
      id
      vault {
        id
        symbol
        asset {
          symbol
          name
        }
      }
      balance
      balanceFormatted
    }
  }
}
```

## Interprétation des Résultats

### Réponse API

La réponse contient :
- `mainAddress`: L'adresse principale du compte
- `deposits`: Tableau des positions de dépôt (IDs)
- `borrows`: Tableau des positions d'emprunt (IDs)

### Exemple de Sortie

```
🔍 Analyse des positions pour: 0x66DbceE7feA3287B3356227d6F3DfF3CeFbC6F3C
📡 Endpoint: https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-mainnet/latest/gn
--------------------------------------------------------------------------------
✅ Positions trouvées pour: 0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3c
================================================================================

💰 DÉPÔTS (2 positions):
   1. Position ID: 0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3d46bc453666ba11b4b08b0804e49a9d797546ee7d
      👤 Sub-Account: 0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3c
      🏦 Vault: 0x46bc453666ba11b4b08b0804e49a9d797546ee7d

🏦 EMPRUNTS (2 positions):
   1. Position ID: 0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3dc2c4abae84fbb5b7baab52301a924b1f986c66bd
      👤 Sub-Account: 0x66dbcee7fea3287b3356227d6f3dff3cefbc6f3c
      🏦 Vault: 0xc2c4abae84fbb5b7baab52301a924b1f986c66bd

📊 RÉSUMÉ:
   - Total positions: 4
   - Dépôts: 2
   - Emprunts: 2
   - Vaults uniques: 4
   - Sub-accounts uniques: 1
   - Statut: 🟢 Actif sur Euler v2
```

## Dépendances

Le client utilise la bibliothèque `requests` qui est déjà incluse dans le `requirements.txt` du projet. 