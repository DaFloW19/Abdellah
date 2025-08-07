import schedule
import time
import threading
from datetime import datetime, timedelta
from config import Config
from models import get_session, create_database, Property
from airbnb_scraper import AirbnbScraper
from pricing_algorithm import PricingAlgorithm
from airbnb_api import AirbnbAPI
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PricingScheduler:
    def __init__(self):
        self.config = Config()
        self.engine = create_database(self.config.DATABASE_URL)
        self.scraper = None
        self.pricing_algorithm = PricingAlgorithm()
        self.airbnb_api = None
        self.is_running = False
        self.last_competitor_scan = None
        self.last_price_update = None
        
    def start_monitoring(self):
        """Démarre la surveillance continue"""
        logger.info("🚀 Démarrage du système de surveillance automatisée des prix Airbnb")
        
        # Planifier les tâches
        self.schedule_tasks()
        
        # Démarrer la boucle de surveillance
        self.is_running = True
        
        # Exécuter les tâches dans un thread séparé
        monitoring_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        monitoring_thread.start()
        
        logger.info("✅ Surveillance démarrée avec succès")
        
        # Exécuter une première analyse immédiatement
        self.run_initial_analysis()
        
        return monitoring_thread
    
    def schedule_tasks(self):
        """Configure la planification des tâches"""
        
        # Scan des concurrents toutes les 30 minutes
        schedule.every(30).minutes.do(self.scan_competitors)
        
        # Calcul et mise à jour des prix toutes les heures
        schedule.every().hour.do(self.update_all_prices)
        
        # Synchronisation des propriétés Airbnb toutes les 6 heures
        schedule.every(6).hours.do(self.sync_airbnb_properties)
        
        # Rapport quotidien à 9h00
        schedule.every().day.at("09:00").do(self.send_daily_report)
        
        # Nettoyage des données anciennes chaque dimanche à 02:00
        schedule.every().sunday.at("02:00").do(self.cleanup_old_data)
        
        # Vérification de santé du système toutes les 15 minutes
        schedule.every(15).minutes.do(self.health_check)
        
        logger.info("📅 Tâches programmées configurées:")
        logger.info("   - Scan concurrents: toutes les 30 minutes")
        logger.info("   - Mise à jour prix: toutes les heures")
        logger.info("   - Sync propriétés: toutes les 6 heures")
        logger.info("   - Rapport quotidien: 09:00")
        logger.info("   - Nettoyage: dimanche 02:00")
    
    def run_scheduler(self):
        """Exécute la boucle principale du planificateur"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Vérifier toutes les minutes
            except Exception as e:
                logger.error(f"Erreur dans la boucle du planificateur: {e}")
                time.sleep(60)
    
    def run_initial_analysis(self):
        """Exécute une analyse initiale complète"""
        logger.info("🔍 Exécution de l'analyse initiale...")
        
        try:
            # Synchroniser les propriétés
            self.sync_airbnb_properties()
            
            # Scanner les concurrents
            self.scan_competitors()
            
            # Calculer les prix optimaux
            self.calculate_optimal_prices()
            
            logger.info("✅ Analyse initiale terminée")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse initiale: {e}")
    
    def scan_competitors(self):
        """Scanne les prix des concurrents"""
        logger.info("🔍 Début du scan des concurrents...")
        
        try:
            if not self.scraper:
                self.scraper = AirbnbScraper()
                if not self.scraper.login_to_airbnb():
                    logger.error("Impossible de se connecter à Airbnb pour le scraping")
                    return False
            
            db_session = get_session(self.engine)
            
            # Récupérer toutes les propriétés actives
            properties = db_session.query(Property).filter_by(is_active=True).all()
            
            total_competitors_found = 0
            
            for property_obj in properties:
                try:
                    logger.info(f"Scan des concurrents pour: {property_obj.title}")
                    
                    # Données de la propriété pour la recherche
                    property_data = {
                        'address': property_obj.address or self.config.DEFAULT_CITY,
                        'max_guests': property_obj.max_guests or 4,
                        'bedrooms': property_obj.bedrooms or 2,
                        'property_type': property_obj.property_type or 'apartment'
                    }
                    
                    # Rechercher les concurrents
                    competitors = self.scraper.search_competitors(property_data)
                    
                    if competitors:
                        # Sauvegarder les données des concurrents
                        self.scraper.save_competitor_data(property_obj.id, competitors)
                        total_competitors_found += len(competitors)
                        logger.info(f"Trouvé {len(competitors)} concurrents pour {property_obj.title}")
                    
                    # Pause entre les propriétés
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Erreur lors du scan pour la propriété {property_obj.id}: {e}")
                    continue
            
            db_session.close()
            
            self.last_competitor_scan = datetime.now()
            logger.info(f"✅ Scan terminé - {total_competitors_found} concurrents trouvés au total")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du scan des concurrents: {e}")
            return False
    
    def calculate_optimal_prices(self):
        """Calcule les prix optimaux pour toutes les propriétés"""
        logger.info("💰 Calcul des prix optimaux...")
        
        try:
            db_session = get_session(self.engine)
            properties = db_session.query(Property).filter_by(is_active=True).all()
            
            recommendations = []
            
            for property_obj in properties:
                try:
                    result = self.pricing_algorithm.calculate_optimal_price(property_obj.id)
                    
                    if result:
                        recommendations.append(result)
                        logger.info(f"Prix optimal calculé pour {property_obj.title}: {result['recommended_price']}€")
                    
                except Exception as e:
                    logger.error(f"Erreur calcul prix pour propriété {property_obj.id}: {e}")
                    continue
            
            db_session.close()
            
            logger.info(f"✅ Prix optimaux calculés pour {len(recommendations)} propriétés")
            return recommendations
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des prix optimaux: {e}")
            return []
    
    def update_all_prices(self):
        """Met à jour automatiquement tous les prix sur Airbnb"""
        logger.info("🔄 Mise à jour automatique des prix...")
        
        try:
            # Calculer les prix optimaux
            recommendations = self.calculate_optimal_prices()
            
            if not recommendations:
                logger.warning("Aucune recommandation de prix disponible")
                return False
            
            # Initialiser l'API Airbnb si nécessaire
            if not self.airbnb_api:
                self.airbnb_api = AirbnbAPI()
            
            updates_made = 0
            total_savings = 0
            
            for recommendation in recommendations:
                try:
                    property_id = recommendation['property_id']
                    current_price = recommendation['current_price'] or 0
                    recommended_price = recommendation['recommended_price']
                    
                    # Vérifier si un changement est nécessaire
                    if not recommendation.get('price_change_needed', False):
                        logger.info(f"Propriété {property_id}: aucun changement nécessaire")
                        continue
                    
                    # Vérifier la confiance dans la recommandation
                    confidence = recommendation.get('confidence_score', 0)
                    if confidence < 0.3:  # Seuil de confiance minimum
                        logger.warning(f"Propriété {property_id}: confiance trop faible ({confidence:.2f})")
                        continue
                    
                    # Mettre à jour le prix sur Airbnb
                    success = self.airbnb_api.update_property_price_on_airbnb(
                        property_id, 
                        recommended_price,
                        "Automatic optimization based on competitor analysis"
                    )
                    
                    if success:
                        updates_made += 1
                        price_diff = recommended_price - current_price
                        total_savings += price_diff
                        
                        logger.info(f"✅ Prix mis à jour - Propriété {property_id}: "
                                  f"{current_price}€ → {recommended_price}€ ({price_diff:+.2f}€)")
                    else:
                        logger.error(f"❌ Échec mise à jour prix - Propriété {property_id}")
                    
                    # Pause entre les mises à jour
                    time.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Erreur mise à jour propriété {property_id}: {e}")
                    continue
            
            self.last_price_update = datetime.now()
            
            logger.info(f"✅ Mise à jour terminée - {updates_made} prix modifiés")
            logger.info(f"💰 Impact total estimé: {total_savings:+.2f}€")
            
            # Envoyer une notification si des changements ont été faits
            if updates_made > 0:
                self.send_price_update_notification(updates_made, total_savings)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des prix: {e}")
            return False
    
    def sync_airbnb_properties(self):
        """Synchronise les propriétés depuis Airbnb"""
        logger.info("🔄 Synchronisation des propriétés Airbnb...")
        
        try:
            if not self.airbnb_api:
                self.airbnb_api = AirbnbAPI()
            
            success = self.airbnb_api.sync_properties_from_airbnb()
            
            if success:
                logger.info("✅ Synchronisation des propriétés terminée")
            else:
                logger.error("❌ Échec de la synchronisation des propriétés")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {e}")
            return False
    
    def health_check(self):
        """Vérifie la santé du système"""
        try:
            # Vérifier la connexion à la base de données
            db_session = get_session(self.engine)
            property_count = db_session.query(Property).count()
            db_session.close()
            
            # Vérifier les dernières activités
            now = datetime.now()
            competitor_scan_delay = (now - self.last_competitor_scan).total_seconds() / 3600 if self.last_competitor_scan else 999
            price_update_delay = (now - self.last_price_update).total_seconds() / 3600 if self.last_price_update else 999
            
            # Alertes si les délais sont trop longs
            if competitor_scan_delay > 2:  # Plus de 2 heures sans scan
                logger.warning(f"⚠️ Dernier scan concurrents il y a {competitor_scan_delay:.1f}h")
            
            if price_update_delay > 4:  # Plus de 4 heures sans mise à jour
                logger.warning(f"⚠️ Dernière mise à jour prix il y a {price_update_delay:.1f}h")
            
            logger.debug(f"💓 Système en fonctionnement - {property_count} propriétés surveillées")
            
        except Exception as e:
            logger.error(f"Erreur lors du health check: {e}")
    
    def send_daily_report(self):
        """Envoie un rapport quotidien par email"""
        logger.info("📧 Envoi du rapport quotidien...")
        
        try:
            # Générer le rapport
            report = self.generate_daily_report()
            
            # Envoyer par email (optionnel - nécessite configuration SMTP)
            # self.send_email_report(report)
            
            # Pour l'instant, juste logger le rapport
            logger.info("📊 RAPPORT QUOTIDIEN:")
            logger.info(report)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du rapport: {e}")
    
    def generate_daily_report(self):
        """Génère un rapport quotidien des activités"""
        try:
            db_session = get_session(self.engine)
            
            # Statistiques des propriétés
            total_properties = db_session.query(Property).filter_by(is_active=True).count()
            
            # Statistiques des dernières 24h
            yesterday = datetime.now() - timedelta(days=1)
            
            from models import PriceHistory, MarketAnalytics
            
            recent_price_changes = db_session.query(PriceHistory).filter(
                PriceHistory.created_at >= yesterday
            ).count()
            
            recent_analytics = db_session.query(MarketAnalytics).filter(
                MarketAnalytics.created_at >= yesterday
            ).count()
            
            db_session.close()
            
            report = f"""
📊 RAPPORT QUOTIDIEN AIRBNB - {datetime.now().strftime('%d/%m/%Y')}

🏠 Propriétés surveillées: {total_properties}
💰 Changements de prix (24h): {recent_price_changes}
📈 Analyses de marché (24h): {recent_analytics}

🔍 Dernier scan concurrents: {self.last_competitor_scan.strftime('%d/%m/%Y %H:%M') if self.last_competitor_scan else 'Jamais'}
💲 Dernière mise à jour prix: {self.last_price_update.strftime('%d/%m/%Y %H:%M') if self.last_price_update else 'Jamais'}

✅ Système opérationnel
            """.strip()
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur génération rapport: {e}")
            return "Erreur lors de la génération du rapport"
    
    def send_price_update_notification(self, updates_count, total_impact):
        """Envoie une notification après mise à jour des prix"""
        message = f"""
🔔 NOTIFICATION PRIX AIRBNB

✅ {updates_count} prix mis à jour automatiquement
💰 Impact estimé: {total_impact:+.2f}€
🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}

Consultez le tableau de bord pour plus de détails.
        """.strip()
        
        logger.info(message)
        # Ici vous pourriez ajouter l'envoi par email, SMS, Slack, etc.
    
    def cleanup_old_data(self):
        """Nettoie les anciennes données"""
        logger.info("🧹 Nettoyage des anciennes données...")
        
        try:
            db_session = get_session(self.engine)
            
            # Supprimer les prix des concurrents de plus de 30 jours
            cutoff_date = datetime.now() - timedelta(days=30)
            
            from models import CompetitorPrice, MarketAnalytics
            
            old_prices = db_session.query(CompetitorPrice).filter(
                CompetitorPrice.scraped_at < cutoff_date
            ).delete()
            
            # Supprimer les analytics de plus de 90 jours
            analytics_cutoff = datetime.now() - timedelta(days=90)
            old_analytics = db_session.query(MarketAnalytics).filter(
                MarketAnalytics.created_at < analytics_cutoff
            ).delete()
            
            db_session.commit()
            db_session.close()
            
            logger.info(f"✅ Nettoyage terminé - {old_prices} prix supprimés, {old_analytics} analytics supprimées")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
    
    def stop_monitoring(self):
        """Arrête la surveillance"""
        logger.info("🛑 Arrêt de la surveillance...")
        
        self.is_running = False
        
        # Nettoyer les ressources
        if self.scraper:
            self.scraper.cleanup()
        
        if self.airbnb_api:
            self.airbnb_api.cleanup()
        
        logger.info("✅ Surveillance arrêtée")

def main():
    """Fonction principale pour démarrer le système"""
    scheduler = PricingScheduler()
    
    try:
        # Démarrer la surveillance
        monitoring_thread = scheduler.start_monitoring()
        
        logger.info("🎯 Système de surveillance automatisée démarré")
        logger.info("📊 Accédez au tableau de bord: http://localhost:8050")
        logger.info("🔄 Le système fonctionne en arrière-plan")
        logger.info("⏹️  Appuyez sur Ctrl+C pour arrêter")
        
        # Maintenir le programme en vie
        while scheduler.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt demandé par l'utilisateur")
        scheduler.stop_monitoring()
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        scheduler.stop_monitoring()

if __name__ == "__main__":
    main()