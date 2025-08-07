#!/usr/bin/env python3
"""
Script de démarrage pour le système de gestion automatique des prix Airbnb
Compte: miftah.conciergerie@gmail.com
"""

import sys
import os
import asyncio
import signal
import logging
from pathlib import Path

# Ajouter le répertoire racine au PATH
sys.path.append(str(Path(__file__).parent))

def setup_logging():
    """Configuration du système de logs"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('airbnb_pricing.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_dependencies():
    """Vérifier que toutes les dépendances sont installées"""
    required_packages = [
        'fastapi', 'uvicorn', 'selenium', 'beautifulsoup4', 
        'pandas', 'numpy', 'sqlalchemy', 'requests', 'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Packages manquants:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n💡 Installez les dépendances avec:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_chrome_driver():
    """Vérifier que ChromeDriver est disponible"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.quit()
        return True
        
    except Exception as e:
        print("❌ ChromeDriver n'est pas disponible:")
        print(f"   Erreur: {e}")
        print("\n💡 Installez ChromeDriver:")
        print("   - Ubuntu: sudo apt-get install chromium-chromedriver")
        print("   - MacOS: brew install chromedriver")
        print("   - Windows: Téléchargez depuis https://chromedriver.chromium.org/")
        return False

def create_demo_data():
    """Créer des données de démonstration si nécessaire"""
    from database.models import init_db, get_session, PriceHistory
    from datetime import datetime, timedelta
    import random
    
    # Initialiser la base de données
    init_db()
    
    session = get_session()
    
    # Vérifier s'il y a déjà des données
    existing_data = session.query(PriceHistory).count()
    
    if existing_data == 0:
        print("📊 Création de données de démonstration...")
        
        # Créer 30 jours de données historiques
        base_price = 85
        for i in range(30):
            date = datetime.now() - timedelta(days=30-i)
            
            # Simuler des variations de prix réalistes
            seasonal_factor = 1 + 0.2 * (i / 30)  # Tendance à la hausse
            noise = random.uniform(-0.1, 0.1)
            
            current_price = base_price * seasonal_factor * (1 + noise)
            competitor_avg = current_price * random.uniform(0.9, 1.1)
            recommended = competitor_avg * random.uniform(0.95, 1.05)
            
            history_entry = PriceHistory(
                timestamp=date,
                listing_id="demo_listing",
                current_price=round(current_price, 2),
                recommended_price=round(recommended, 2),
                competitor_average=round(competitor_avg, 2),
                competitor_median=round(competitor_avg * 0.98, 2),
                competitor_count=random.randint(15, 25),
                confidence=random.randint(60, 95),
                reasoning=f"Prix basé sur {random.randint(15, 25)} concurrents",
                auto_updated=random.choice([True, False])
            )
            
            session.add(history_entry)
        
        session.commit()
        print("✅ Données de démonstration créées")
    
    session.close()

def start_application():
    """Démarrer l'application principale"""
    print("🚀 Démarrage du système de gestion automatique des prix Airbnb")
    print("=" * 60)
    print("📧 Compte: miftah.conciergerie@gmail.com")
    print("🎯 Fonctionnalités:")
    print("   ✓ Surveillance automatique des prix concurrents")
    print("   ✓ Calcul intelligent du prix optimal")
    print("   ✓ Tableau de bord en temps réel")
    print("   ✓ Mise à jour automatique des prix")
    print("=" * 60)
    
    # Démarrer le serveur FastAPI
    import uvicorn
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Désactivé pour la production
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du serveur...")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
        sys.exit(1)

def main():
    """Fonction principale"""
    print("🔧 Initialisation du système...")
    
    # Configuration des logs
    setup_logging()
    
    # Vérifications des prérequis
    if not check_dependencies():
        sys.exit(1)
    
    if not check_chrome_driver():
        print("⚠️  Warning: ChromeDriver non disponible, fonctionnalité de scraping limitée")
    
    # Créer des données de démo si nécessaire
    try:
        create_demo_data()
    except Exception as e:
        print(f"⚠️  Warning: Erreur lors de la création des données de démo: {e}")
    
    # Afficher les informations de connexion
    print("\n🌐 Le tableau de bord sera disponible sur:")
    print("   http://localhost:8000")
    print("   http://0.0.0.0:8000")
    print("\n📊 API disponible sur:")
    print("   http://localhost:8000/docs")
    print("\n⚠️  IMPORTANT:")
    print("   - Assurez-vous d'avoir une connexion internet stable")
    print("   - Le premier scan peut prendre quelques minutes")
    print("   - Consultez le fichier airbnb_pricing.log pour les détails")
    print("\nAppuyez sur Ctrl+C pour arrêter le serveur")
    print("=" * 60)
    
    # Démarrer l'application
    start_application()

if __name__ == "__main__":
    main()