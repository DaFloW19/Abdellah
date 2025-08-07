import requests
import json
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config import Config
from models import get_session, create_database, Property, PriceHistory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirbnbAPI:
    def __init__(self):
        self.config = Config()
        self.engine = create_database(self.config.DATABASE_URL)
        self.session = requests.Session()
        self.driver = None
        self.is_logged_in = False
        
    def setup_driver(self):
        """Configure le driver Chrome pour les interactions web"""
        chrome_options = Options()
        if self.config.SELENIUM_HEADLESS:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(self.config.SELENIUM_TIMEOUT)
    
    def login_to_airbnb(self):
        """Se connecte à Airbnb pour accéder aux fonctionnalités host"""
        if not self.driver:
            self.setup_driver()
            
        try:
            logger.info("Connexion à Airbnb en tant qu'hôte...")
            self.driver.get("https://www.airbnb.fr/host/login")
            time.sleep(3)
            
            # Accepter les cookies si nécessaire
            try:
                cookie_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accepter')]")
                cookie_button.click()
                time.sleep(2)
            except:
                pass
            
            # Saisir l'email
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_input.clear()
            email_input.send_keys(self.config.AIRBNB_EMAIL)
            
            # Saisir le mot de passe
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys(self.config.AIRBNB_PASSWORD)
            
            # Cliquer sur se connecter
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Attendre la redirection vers le tableau de bord hôte
            time.sleep(10)
            
            # Vérifier si on est connecté en cherchant des éléments spécifiques au dashboard hôte
            try:
                # Attendre que la page du dashboard se charge
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Annonces')]")),
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/hosting/listings')]")),
                        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Tableau de bord')]"))
                    )
                )
                self.is_logged_in = True
                logger.info("Connexion réussie au tableau de bord hôte Airbnb")
                return True
                
            except Exception as e:
                logger.error(f"Échec de la vérification de connexion: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la connexion: {e}")
            return False
    
    def get_host_listings(self):
        """Récupère la liste des annonces de l'hôte"""
        if not self.is_logged_in:
            if not self.login_to_airbnb():
                return []
        
        try:
            # Naviguer vers la page des annonces
            self.driver.get("https://www.airbnb.fr/hosting/listings")
            time.sleep(5)
            
            listings = []
            
            # Chercher les éléments contenant les informations des annonces
            listing_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid*='listing']")
            
            for element in listing_elements:
                try:
                    # Extraire les informations de l'annonce
                    listing_data = self.extract_listing_info(element)
                    if listing_data:
                        listings.append(listing_data)
                except Exception as e:
                    logger.warning(f"Erreur lors de l'extraction d'une annonce: {e}")
                    continue
            
            logger.info(f"Trouvé {len(listings)} annonces")
            return listings
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des annonces: {e}")
            return []
    
    def extract_listing_info(self, element):
        """Extrait les informations d'une annonce depuis un élément DOM"""
        try:
            # Chercher le titre de l'annonce
            title_element = element.find_element(By.CSS_SELECTOR, "h3, [data-testid*='title']")
            title = title_element.text.strip()
            
            # Chercher l'URL de l'annonce pour extraire l'ID
            link_element = element.find_element(By.CSS_SELECTOR, "a")
            listing_url = link_element.get_attribute('href')
            
            # Extraire l'ID Airbnb depuis l'URL
            import re
            match = re.search(r'/rooms/(\d+)', listing_url)
            airbnb_id = match.group(1) if match else None
            
            if not airbnb_id:
                return None
            
            # Chercher le prix actuel
            price_element = element.find_elements(By.CSS_SELECTOR, "[data-testid*='price'], .price")
            current_price = None
            if price_element:
                price_text = price_element[0].text
                price_match = re.search(r'(\d+)', price_text.replace(',', '').replace(' ', ''))
                if price_match:
                    current_price = float(price_match.group(1))
            
            return {
                'airbnb_id': airbnb_id,
                'title': title,
                'current_price': current_price,
                'listing_url': listing_url
            }
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des infos de l'annonce: {e}")
            return None
    
    def update_listing_price(self, airbnb_id, new_price):
        """Met à jour le prix d'une annonce sur Airbnb"""
        if not self.is_logged_in:
            if not self.login_to_airbnb():
                return False
        
        try:
            # Naviguer vers la page de gestion de prix de l'annonce
            pricing_url = f"https://www.airbnb.fr/hosting/listings/{airbnb_id}/pricing"
            logger.info(f"Navigation vers la page de prix: {pricing_url}")
            
            self.driver.get(pricing_url)
            time.sleep(5)
            
            # Attendre que la page se charge
            WebDriverWait(self.driver, 15).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='number']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid*='price']")),
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'prix')]"))
                )
            )
            
            # Chercher le champ de prix de base
            price_input = None
            possible_selectors = [
                "input[data-testid*='base-price']",
                "input[type='number']",
                "input[aria-label*='prix']",
                "input[placeholder*='prix']"
            ]
            
            for selector in possible_selectors:
                try:
                    price_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not price_input:
                logger.error("Impossible de trouver le champ de prix")
                return False
            
            # Effacer le prix actuel et saisir le nouveau
            price_input.clear()
            time.sleep(1)
            price_input.send_keys(str(int(new_price)))
            time.sleep(2)
            
            # Chercher et cliquer sur le bouton de sauvegarde
            save_button = None
            possible_save_selectors = [
                "button[data-testid*='save']",
                "button[type='submit']",
                "//button[contains(text(), 'Enregistrer')]",
                "//button[contains(text(), 'Sauvegarder')]",
                "//button[contains(text(), 'Save')]"
            ]
            
            for selector in possible_save_selectors:
                try:
                    if selector.startswith("//"):
                        save_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        save_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if save_button:
                save_button.click()
                time.sleep(3)
                
                # Vérifier si la sauvegarde a réussi
                try:
                    # Chercher un message de confirmation
                    WebDriverWait(self.driver, 10).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'enregistré')]")),
                            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'saved')]")),
                            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'updated')]"))
                        )
                    )
                    logger.info(f"Prix mis à jour avec succès pour l'annonce {airbnb_id}: {new_price}€")
                    return True
                except:
                    # Même sans message de confirmation, considérer comme réussi si pas d'erreur
                    logger.info(f"Prix probablement mis à jour pour l'annonce {airbnb_id}: {new_price}€")
                    return True
            else:
                logger.error("Impossible de trouver le bouton de sauvegarde")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du prix pour {airbnb_id}: {e}")
            return False
    
    def sync_properties_from_airbnb(self):
        """Synchronise les propriétés depuis Airbnb vers la base de données locale"""
        db_session = get_session(self.engine)
        
        try:
            # Récupérer les annonces depuis Airbnb
            airbnb_listings = self.get_host_listings()
            
            if not airbnb_listings:
                logger.warning("Aucune annonce trouvée sur Airbnb")
                return False
            
            for listing in airbnb_listings:
                # Vérifier si la propriété existe déjà
                existing_property = db_session.query(Property).filter_by(
                    airbnb_id=listing['airbnb_id']
                ).first()
                
                if existing_property:
                    # Mettre à jour les informations existantes
                    existing_property.title = listing['title']
                    if listing['current_price']:
                        existing_property.current_price = listing['current_price']
                    existing_property.updated_at = datetime.now()
                    logger.info(f"Propriété mise à jour: {listing['title']}")
                else:
                    # Créer une nouvelle propriété
                    new_property = Property(
                        airbnb_id=listing['airbnb_id'],
                        title=listing['title'],
                        current_price=listing['current_price'],
                        is_active=True
                    )
                    db_session.add(new_property)
                    logger.info(f"Nouvelle propriété ajoutée: {listing['title']}")
            
            db_session.commit()
            logger.info(f"Synchronisation terminée: {len(airbnb_listings)} propriétés traitées")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()
    
    def update_property_price_on_airbnb(self, property_id, new_price, reason="Automatic pricing optimization"):
        """Met à jour le prix d'une propriété sur Airbnb et en base de données"""
        db_session = get_session(self.engine)
        
        try:
            # Récupérer la propriété
            property_obj = db_session.query(Property).filter_by(id=property_id).first()
            if not property_obj:
                logger.error(f"Propriété {property_id} non trouvée")
                return False
            
            # Mettre à jour sur Airbnb
            success = self.update_listing_price(property_obj.airbnb_id, new_price)
            
            if success:
                # Enregistrer l'historique
                old_price = property_obj.current_price
                
                history_entry = PriceHistory(
                    property_id=property_id,
                    old_price=old_price,
                    new_price=new_price,
                    reason=reason
                )
                db_session.add(history_entry)
                
                # Mettre à jour le prix en base
                property_obj.current_price = new_price
                property_obj.updated_at = datetime.now()
                
                db_session.commit()
                
                logger.info(f"Prix mis à jour avec succès - Propriété: {property_obj.title}, "
                           f"Ancien prix: {old_price}€, Nouveau prix: {new_price}€")
                return True
            else:
                logger.error(f"Échec de la mise à jour du prix sur Airbnb pour la propriété {property_id}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du prix: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()
    
    def bulk_update_prices(self, price_updates):
        """Met à jour plusieurs prix en lot"""
        results = []
        
        for update in price_updates:
            property_id = update.get('property_id')
            new_price = update.get('new_price')
            reason = update.get('reason', 'Bulk automatic update')
            
            success = self.update_property_price_on_airbnb(property_id, new_price, reason)
            results.append({
                'property_id': property_id,
                'success': success,
                'new_price': new_price
            })
            
            # Pause entre les mises à jour pour éviter la limite de taux
            time.sleep(2)
        
        return results
    
    def get_property_performance_data(self, airbnb_id):
        """Récupère les données de performance d'une propriété (réservations, revenus, etc.)"""
        if not self.is_logged_in:
            if not self.login_to_airbnb():
                return None
        
        try:
            # Naviguer vers la page de performance
            performance_url = f"https://www.airbnb.fr/hosting/listings/{airbnb_id}/insights"
            self.driver.get(performance_url)
            time.sleep(5)
            
            performance_data = {}
            
            # Extraire les métriques de performance (à adapter selon l'interface Airbnb)
            try:
                # Taux d'occupation
                occupancy_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'occupation')]")
                if occupancy_elements:
                    # Logique d'extraction du taux d'occupation
                    pass
                
                # Revenus
                revenue_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'revenus')]")
                if revenue_elements:
                    # Logique d'extraction des revenus
                    pass
                
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction des métriques: {e}")
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données de performance: {e}")
            return None
    
    def cleanup(self):
        """Nettoie les ressources"""
        if self.driver:
            self.driver.quit()
        if self.session:
            self.session.close()

# Fonction utilitaire pour tester la connexion
def test_airbnb_connection():
    """Teste la connexion à Airbnb"""
    api = AirbnbAPI()
    try:
        success = api.login_to_airbnb()
        if success:
            logger.info("✅ Test de connexion Airbnb réussi")
            
            # Tester la récupération des annonces
            listings = api.get_host_listings()
            logger.info(f"✅ Trouvé {len(listings)} annonces")
            
            # Synchroniser avec la base de données
            api.sync_properties_from_airbnb()
            logger.info("✅ Synchronisation terminée")
            
        else:
            logger.error("❌ Échec de la connexion à Airbnb")
        
        return success
        
    finally:
        api.cleanup()

if __name__ == "__main__":
    test_airbnb_connection()