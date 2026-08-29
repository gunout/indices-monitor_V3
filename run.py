#!/usr/bin/env python3
# run.py - Script de lancement pour Indices Monitor

import subprocess
import sys
import os

def check_dependencies():
    """Vérifie et installe les dépendances"""
    try:
        import flask
        import yfinance
        import pandas
        print("✅ Toutes les dépendances sont installées")
        return True
    except ImportError as e:
        print(f"⚠️ Dépendance manquante: {e}")
        print("📦 Installation des dépendances...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True

def main():
    print("=" * 70)
    print("🚀 INDICES MONITOR - Lancement")
    print("=" * 70)
    
    # Vérifier les dépendances
    check_dependencies()
    
    # Lancer le serveur
    print("🔄 Démarrage du serveur Flask...")
    subprocess.run([sys.executable, "serv.py"])

if __name__ == "__main__":
    main()