#!/usr/bin/env python3
"""
Système de Gestion Automatisée des Prix Airbnb - Miftah Conciergerie

Ce script principal permet de lancer les différents composants du système:
- Tableau de bord en temps réel
- Surveillance automatique des prix
- Tests de connexion
- Synchronisation initiale

Auteur: Assistant IA
Date: 2024
"""

import sys
import argparse
import threading
import time
import logging
from datetime import datetime

# Imports des modules du système
from config import Config
from dashboard import AirbnbDashboard
from scheduler import PricingScheduler
from airbnb_api import test_airbnb_connection
from models import create_database

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('airbnb_pricing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AirbnbPricingSystem:
    def __init__(self):
        self.config = Config()
        self.dashboard = None
        self.scheduler = None
        self.dashboard_thread = None
        self.monitoring_thread = None
        
    def print_banner(self):
        """Affiche la bannière du système"""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                   🏠 SYSTÈME DE GESTION AUTOMATISÉE DES PRIX AIRBNB 🏠        ║
║                              Miftah Conciergerie                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  📊 Analyse en temps réel des concurrents                                     ║
║  💰 Optimisation automatique des tarifs                                       ║
║  🎯 Maximisation des revenus                                                  ║
║  📈 Tableau de bord interactif                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        print(banner)
        
    def initialize_system(self):
        """Initialise le système et vérifie la configuration"""
        logger.info("🔧 Initialisation du système...")
        
        try:
            # Créer la base de données
            create_database(self.config.DATABASE_URL)
            logger.info("✅ Base de données initialisée")
            
            # Vérifier la configuration
            self.check_configuration()
            
            logger.info("✅ Système initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation: {e}")
            return False
    
    def check_configuration(self):
        """Vérifie la configuration système"""
        logger.info("🔍 Vérification de la configuration...")
        
        # Vérifier les identifiants Airbnb
        if not self.config.AIRBNB_EMAIL or not self.config.AIRBNB_PASSWORD:
            logger.warning("⚠️ Identifiants Airbnb non configurés dans .env")
        else:
            logger.info("✅ Identifiants Airbnb configurés")
        
        # Vérifier les paramètres de pricing
        logger.info(f"💰 Seuil prix minimum: {self.config.MIN_PRICE_THRESHOLD}€")
        logger.info(f"💰 Seuil prix maximum: {self.config.MAX_PRICE_THRESHOLD}€")
        logger.info(f"📊 Limite changement prix: {self.config.PRICE_CHANGE_LIMIT * 100}%")
        
    def test_connection(self):
        """Teste la connexion à Airbnb"""
        logger.info("🔗 Test de connexion à Airbnb...")
        return test_airbnb_connection()
    
    def start_dashboard(self, host='0.0.0.0', port=8050):
        """Lance le tableau de bord"""
        logger.info(f"📊 Lancement du tableau de bord sur http://{host}:{port}")
        
        try:
            self.dashboard = AirbnbDashboard()
            
            # Lancer dans un thread séparé si nécessaire
            if threading.current_thread() is not threading.main_thread():
                self.dashboard.run(debug=False, host=host, port=port)
            else:
                self.dashboard_thread = threading.Thread(
                    target=lambda: self.dashboard.run(debug=False, host=host, port=port),
                    daemon=True
                )
                self.dashboard_thread.start()
                return self.dashboard_thread
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du lancement du tableau de bord: {e}")
            return None
    
    def start_monitoring(self):
        """Lance la surveillance automatique"""
        logger.info("🤖 Lancement de la surveillance automatique...")
        
        try:
            self.scheduler = PricingScheduler()
            self.monitoring_thread = self.scheduler.start_monitoring()
            return self.monitoring_thread
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du lancement de la surveillance: {e}")
            return None
    
    def start_full_system(self, dashboard_host='0.0.0.0', dashboard_port=8050):
        """Lance le système complet (dashboard + surveillance)"""
        logger.info("🚀 Lancement du système complet...")
        
        # Lancer le tableau de bord
        dashboard_thread = self.start_dashboard(dashboard_host, dashboard_port)
        if not dashboard_thread:
            logger.error("❌ Impossible de lancer le tableau de bord")
            return False
        
        # Lancer la surveillance
        monitoring_thread = self.start_monitoring()
        if not monitoring_thread:
            logger.error("❌ Impossible de lancer la surveillance")
            return False
        
        logger.info("✅ Système complet lancé avec succès")
        logger.info(f"📊 Tableau de bord: http://{dashboard_host}:{dashboard_port}")
        logger.info("🤖 Surveillance automatique: Active")
        
        return True
    
    def stop_system(self):
        """Arrête tous les composants du système"""
        logger.info("🛑 Arrêt du système...")
        
        if self.scheduler:
            self.scheduler.stop_monitoring()
        
        logger.info("✅ Système arrêté")

def main():
    """Fonction principale avec interface en ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Système de Gestion Automatisée des Prix Airbnb - Miftah Conciergerie"
    )
    
    parser.add_argument(
        'mode',
        choices=['dashboard', 'monitor', 'full', 'test', 'init'],
        help='Mode de fonctionnement'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Adresse IP pour le tableau de bord (défaut: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8050,
        help='Port pour le tableau de bord (défaut: 8050)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mode verbose (plus de logs)'
    )
    
    args = parser.parse_args()
    
    # Configuration du niveau de log
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialiser le système
    system = AirbnbPricingSystem()
    system.print_banner()
    
    if not system.initialize_system():
        logger.error("❌ Échec de l'initialisation. Arrêt du programme.")
        sys.exit(1)
    
    try:
        if args.mode == 'init':
            # Mode initialisation uniquement
            logger.info("✅ Initialisation terminée")
            
        elif args.mode == 'test':
            # Mode test de connexion
            success = system.test_connection()
            if success:
                logger.info("✅ Test de connexion réussi")
                sys.exit(0)
            else:
                logger.error("❌ Test de connexion échoué")
                sys.exit(1)
                
        elif args.mode == 'dashboard':
            # Mode tableau de bord uniquement
            system.start_dashboard(args.host, args.port)
            logger.info("⏹️ Appuyez sur Ctrl+C pour arrêter")
            
            # Maintenir le programme en vie
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 Arrêt demandé par l'utilisateur")
                
        elif args.mode == 'monitor':
            # Mode surveillance uniquement
            monitoring_thread = system.start_monitoring()
            if monitoring_thread:
                logger.info("⏹️ Appuyez sur Ctrl+C pour arrêter")
                
                try:
                    while system.scheduler.is_running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("🛑 Arrêt demandé par l'utilisateur")
                    system.stop_system()
            
        elif args.mode == 'full':
            # Mode complet
            success = system.start_full_system(args.host, args.port)
            if success:
                logger.info("⏹️ Appuyez sur Ctrl+C pour arrêter")
                
                try:
                    while system.scheduler.is_running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("🛑 Arrêt demandé par l'utilisateur")
                    system.stop_system()
    
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        system.stop_system()
        sys.exit(1)

if __name__ == "__main__":
    main()