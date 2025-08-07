import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import requests
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class AirbnbClient:
    """Client pour automatiser les interactions avec Airbnb"""
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.driver = None
        self.is_logged_in = False
        self.listings = []
        
    async def _setup_driver(self):
        """Configuration du driver Selenium"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Mode sans interface graphique
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
    async def login(self) -> bool:
        """Connexion à Airbnb"""
        try:
            await self._setup_driver()
            
            logger.info("🔐 Connexion à Airbnb en cours...")
            
            # Aller à la page de connexion
            self.driver.get("https://www.airbnb.fr/login")
            await asyncio.sleep(3)
            
            # Accepter les cookies si nécessaire
            try:
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepter')]"))
                )
                cookie_button.click()
                await asyncio.sleep(2)
            except TimeoutException:
                pass  # Pas de banner de cookies
            
            # Remplir l'email
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_input.clear()
            email_input.send_keys(self.email)
            
            # Remplir le mot de passe
            password_input = self.driver.find_element(By.ID, "password")
            password_input.clear()
            password_input.send_keys(self.password)
            
            # Cliquer sur le bouton de connexion
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Attendre la redirection
            WebDriverWait(self.driver, 15).until(
                EC.url_contains("airbnb.fr")
            )
            
            # Vérifier si la connexion a réussi
            await asyncio.sleep(3)
            current_url = self.driver.current_url
            
            if "login" not in current_url.lower():
                self.is_logged_in = True
                logger.info("✅ Connexion réussie à Airbnb")
                return True
            else:
                logger.error("❌ Échec de la connexion à Airbnb")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la connexion: {e}")
            return False
    
    async def get_listings(self) -> List[Dict]:
        """Récupérer la liste des annonces de l'utilisateur"""
        try:
            if not self.is_logged_in:
                await self.login()
            
            logger.info("📋 Récupération des annonces...")
            
            # Aller à la page de gestion des annonces
            self.driver.get("https://www.airbnb.fr/hosting/listings")
            await asyncio.sleep(5)
            
            # Récupérer les informations des annonces
            listings = []
            
            # Sélecteur pour les cartes d'annonces (peut nécessiter un ajustement)
            listing_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='listing-card']")
            
            for card in listing_cards:
                try:
                    # Extraire les informations de base
                    title_element = card.find_element(By.CSS_SELECTOR, "h3")
                    title = title_element.text if title_element else "Titre non trouvé"
                    
                    # Récupérer le prix actuel
                    price_element = card.find_element(By.CSS_SELECTOR, "[data-testid='price-display']")
                    price_text = price_element.text if price_element else "0"
                    
                    # Extraire le prix numérique
                    price = self._extract_price_from_text(price_text)
                    
                    # Récupérer l'ID de l'annonce depuis l'URL
                    link_element = card.find_element(By.CSS_SELECTOR, "a")
                    listing_url = link_element.get_attribute("href")
                    listing_id = self._extract_listing_id_from_url(listing_url)
                    
                    listing_data = {
                        "id": listing_id,
                        "title": title,
                        "current_price": price,
                        "url": listing_url
                    }
                    
                    listings.append(listing_data)
                    
                except Exception as e:
                    logger.warning(f"Erreur lors de l'extraction d'une annonce: {e}")
                    continue
            
            self.listings = listings
            logger.info(f"✅ {len(listings)} annonce(s) récupérée(s)")
            return listings
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des annonces: {e}")
            return []
    
    async def update_listing_price(self, listing_id: str = None, new_price: float = None) -> bool:
        """Mettre à jour le prix d'une annonce"""
        try:
            if not self.is_logged_in:
                await self.login()
            
            if not self.listings:
                await self.get_listings()
            
            # Utiliser la première annonce si aucun ID spécifié
            if listing_id is None and self.listings:
                listing_id = self.listings[0]["id"]
            
            if not listing_id:
                logger.error("Aucune annonce trouvée pour la mise à jour du prix")
                return False
            
            logger.info(f"💰 Mise à jour du prix de l'annonce {listing_id} vers {new_price}€")
            
            # Aller à la page d'édition du prix
            edit_url = f"https://www.airbnb.fr/hosting/listings/{listing_id}/pricing"
            self.driver.get(edit_url)
            await asyncio.sleep(5)
            
            # Trouver le champ de prix et le mettre à jour
            price_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='price-input']"))
            )
            
            # Effacer et saisir le nouveau prix
            price_input.clear()
            price_input.send_keys(str(int(new_price)))
            
            # Sauvegarder
            save_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='save-button']"))
            )
            save_button.click()
            
            # Attendre la confirmation
            await asyncio.sleep(3)
            
            logger.info(f"✅ Prix mis à jour avec succès: {new_price}€")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du prix: {e}")
            return False
    
    def _extract_price_from_text(self, price_text: str) -> float:
        """Extraire le prix numérique du texte"""
        import re
        # Rechercher les chiffres dans le texte
        numbers = re.findall(r'\d+', price_text.replace(',', '').replace(' ', ''))
        if numbers:
            return float(numbers[0])
        return 0.0
    
    def _extract_listing_id_from_url(self, url: str) -> str:
        """Extraire l'ID de l'annonce depuis l'URL"""
        import re
        match = re.search(r'/listings/(\d+)', url)
        if match:
            return match.group(1)
        return ""
    
    async def close(self):
        """Fermer le driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_logged_in = False