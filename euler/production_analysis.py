#!/usr/bin/env python3
"""
Script simple d'analyse des positions Euler v2 pour l'adresse de production
"""

from vault_info_client import EulerProductionClient, PRODUCTION_ADDRESS

def main():
    print("🚀 Analyse des positions Euler v2 - Adresse de production")
    print("=" * 60)
    
    client = EulerProductionClient()
    
    # Utiliser l'adresse de production automatiquement
    client.analyze_production_positions()

if __name__ == "__main__":
    main() 