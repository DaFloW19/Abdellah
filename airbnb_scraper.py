import requests
import time
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config import Config
from models import get_session, create_database, Competitor, CompetitorPrice, Property
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirbnbScraper:
    def __init__(self):
        self.config = Config()
        self.setup_driver()
        self.session = None
        self.engine = create_database(self.config.DATABASE_URL)
        
    def setup_driver(self):
        """Configure le driver Chrome pour Selenium"""
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
        """Se connecte à Airbnb avec les identifiants fournis"""
        try:
            logger.info("Connexion à Airbnb...")
            self.driver.get("https://www.airbnb.fr/login")
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
            email_input.send_keys(self.config.AIRBNB_EMAIL)
            
            # Saisir le mot de passe
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.send_keys(self.config.AIRBNB_PASSWORD)
            
            # Cliquer sur se connecter
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            time.sleep(5)
            logger.info("Connexion réussie à Airbnb")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la connexion: {e}")
            return False
    
    def search_competitors(self, property_data, check_in_date=None, check_out_date=None):
        """Recherche les concurrents dans la zone de la propriété"""
        if not check_in_date:
            check_in_date = datetime.now() + timedelta(days=7)
        if not check_out_date:
            check_out_date = check_in_date + timedelta(days=1)
        
        try:
            # Construire l'URL de recherche
            location = property_data.get('address', self.config.DEFAULT_CITY)
            guests = property_data.get('max_guests', 4)
            
            search_url = f"https://www.airbnb.fr/s/{location}/homes"
            params = {
                'checkin': check_in_date.strftime('%Y-%m-%d'),
                'checkout': check_out_date.strftime('%Y-%m-%d'),
                'adults': guests,
                'source': 'structured_search_input_header',
                'search_type': 'user_map_move'
            }
            
            # Construire l'URL complète
            url_params = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{search_url}?{url_params}"
            
            logger.info(f"Recherche des concurrents: {full_url}")
            self.driver.get(full_url)
            time.sleep(5)
            
            # Attendre que les résultats se chargent
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='card-container']"))
            )
            
            # Extraire les données des propriétés
            competitors = self.extract_property_data(property_data)
            
            return competitors
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de concurrents: {e}")
            return []
    
    def extract_property_data(self, reference_property):
        """Extrait les données des propriétés depuis la page de résultats"""
        competitors = []
        
        try:
            # Trouver tous les conteneurs de propriétés
            property_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='card-container']")
            
            for card in property_cards[:20]:  # Limiter à 20 propriétés
                try:
                    # Extraire l'ID Airbnb depuis l'URL
                    link_element = card.find_element(By.CSS_SELECTOR, "a")
                    property_url = link_element.get_attribute('href')
                    airbnb_id = self.extract_airbnb_id(property_url)
                    
                    if not airbnb_id:
                        continue
                    
                    # Extraire le titre
                    title_element = card.find_element(By.CSS_SELECTOR, "[data-testid='listing-card-title']")
                    title = title_element.text.strip()
                    
                    # Extraire le prix
                    price_element = card.find_element(By.CSS_SELECTOR, "[data-testid='price-availability']")
                    price = self.extract_price_from_text(price_element.text)
                    
                    # Extraire les détails (chambres, lits, etc.)
                    details = self.extract_property_details(card)
                    
                    # Calculer le score de similarité
                    similarity_score = self.calculate_similarity(reference_property, details)
                    
                    competitor_data = {
                        'airbnb_id': airbnb_id,
                        'title': title,
                        'price': price,
                        'bedrooms': details.get('bedrooms'),
                        'bathrooms': details.get('bathrooms'),
                        'max_guests': details.get('max_guests'),
                        'property_type': details.get('property_type'),
                        'similarity_score': similarity_score,
                        'scraped_at': datetime.now()
                    }
                    
                    competitors.append(competitor_data)
                    
                except Exception as e:
                    logger.warning(f"Erreur lors de l'extraction d'une propriété: {e}")
                    continue
            
            logger.info(f"Trouvé {len(competitors)} concurrents potentiels")
            return competitors
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données: {e}")
            return []
    
    def extract_airbnb_id(self, url):
        """Extrait l'ID Airbnb depuis l'URL"""
        try:
            # Pattern pour extraire l'ID depuis l'URL Airbnb
            match = re.search(r'/rooms/(\d+)', url)
            if match:
                return match.group(1)
            return None
        except:
            return None
    
    def extract_price_from_text(self, price_text):
        """Extrait le prix depuis le texte"""
        try:
            # Chercher le pattern de prix (€XX ou XX €)
            match = re.search(r'(\d+)', price_text.replace(',', '').replace(' ', ''))
            if match:
                return float(match.group(1))
            return None
        except:
            return None
    
    def extract_property_details(self, card):
        """Extrait les détails de la propriété depuis la carte"""
        details = {}
        
        try:
            # Chercher les détails dans le texte de la carte
            text_content = card.text.lower()
            
            # Extraire le nombre de chambres
            bedroom_match = re.search(r'(\d+)\s*chambre', text_content)
            if bedroom_match:
                details['bedrooms'] = int(bedroom_match.group(1))
            
            # Extraire le nombre de salles de bain
            bathroom_match = re.search(r'(\d+)\s*salle', text_content)
            if bathroom_match:
                details['bathrooms'] = int(bathroom_match.group(1))
            
            # Extraire le nombre maximum d'invités
            guest_match = re.search(r'(\d+)\s*voyageur', text_content)
            if guest_match:
                details['max_guests'] = int(guest_match.group(1))
            
            # Type de propriété (appartement, maison, etc.)
            if 'appartement' in text_content:
                details['property_type'] = 'apartment'
            elif 'maison' in text_content:
                details['property_type'] = 'house'
            elif 'studio' in text_content:
                details['property_type'] = 'studio'
            else:
                details['property_type'] = 'other'
                
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des détails: {e}")
        
        return details
    
    def calculate_similarity(self, reference_property, competitor_details):
        """Calcule un score de similarité entre la propriété de référence et un concurrent"""
        score = 0.0
        total_factors = 0
        
        # Comparaison du nombre de chambres
        if reference_property.get('bedrooms') and competitor_details.get('bedrooms'):
            bedroom_diff = abs(reference_property['bedrooms'] - competitor_details['bedrooms'])
            if bedroom_diff == 0:
                score += 0.4
            elif bedroom_diff == 1:
                score += 0.2
            total_factors += 0.4
        
        # Comparaison du nombre d'invités
        if reference_property.get('max_guests') and competitor_details.get('max_guests'):
            guest_diff = abs(reference_property['max_guests'] - competitor_details['max_guests'])
            if guest_diff <= 1:
                score += 0.3
            elif guest_diff <= 2:
                score += 0.15
            total_factors += 0.3
        
        # Comparaison du type de propriété
        if reference_property.get('property_type') and competitor_details.get('property_type'):
            if reference_property['property_type'] == competitor_details['property_type']:
                score += 0.3
            total_factors += 0.3
        
        return score / total_factors if total_factors > 0 else 0.0
    
    def save_competitor_data(self, property_id, competitors_data):
        """Sauvegarde les données des concurrents en base"""
        db_session = get_session(self.engine)
        
        try:
            for competitor_data in competitors_data:
                # Vérifier si le concurrent existe déjà
                existing = db_session.query(Competitor).filter_by(
                    property_id=property_id,
                    airbnb_id=competitor_data['airbnb_id']
                ).first()
                
                if not existing:
                    # Créer un nouveau concurrent
                    competitor = Competitor(
                        property_id=property_id,
                        airbnb_id=competitor_data['airbnb_id'],
                        title=competitor_data['title'],
                        similarity_score=competitor_data['similarity_score'],
                        bedrooms=competitor_data.get('bedrooms'),
                        bathrooms=competitor_data.get('bathrooms'),
                        max_guests=competitor_data.get('max_guests'),
                        property_type=competitor_data.get('property_type')
                    )
                    db_session.add(competitor)
                    db_session.flush()
                    competitor_id = competitor.id
                else:
                    competitor_id = existing.id
                
                # Sauvegarder le prix
                if competitor_data.get('price'):
                    price_entry = CompetitorPrice(
                        competitor_id=competitor_id,
                        price=competitor_data['price'],
                        date_for=datetime.now(),
                        scraped_at=competitor_data['scraped_at']
                    )
                    db_session.add(price_entry)
            
            db_session.commit()
            logger.info(f"Sauvegardé {len(competitors_data)} concurrents pour la propriété {property_id}")
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Erreur lors de la sauvegarde: {e}")
        finally:
            db_session.close()
    
    def cleanup(self):
        """Nettoie les ressources"""
        if self.driver:
            self.driver.quit()
        if self.session:
            self.session.close()

if __name__ == "__main__":
    scraper = AirbnbScraper()
    try:
        # Test de connexion
        if scraper.login_to_airbnb():
            logger.info("Test de connexion réussi")
        else:
            logger.error("Échec de la connexion")
    finally:
        scraper.cleanup()