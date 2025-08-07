import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict, Optional
import re
import numpy as np
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class CompetitorAnalyzer:
    """Analyseur pour surveiller les prix des concurrents sur Airbnb"""
    
    def __init__(self):
        self.driver = None
        self.competitors_cache = []
        self.last_analysis = None
        
    async def _setup_driver(self):
        """Configuration du driver Selenium pour le scraping"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
    
    async def find_competitors(self, location: str, property_type: str = "entire-place", guests: int = 2) -> List[Dict]:
        """Trouver les concurrents directs dans la même zone"""
        try:
            await self._setup_driver()
            
            logger.info(f"🔍 Recherche de concurrents dans la zone: {location}")
            
            # Construire l'URL de recherche Airbnb
            search_url = self._build_search_url(location, property_type, guests)
            
            self.driver.get(search_url)
            await asyncio.sleep(5)
            
            # Accepter les cookies si nécessaire
            try:
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepter') or contains(text(), 'Accept')]"))
                )
                cookie_button.click()
                await asyncio.sleep(2)
            except:
                pass
            
            competitors = []
            
            # Récupérer les cartes de propriétés
            property_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='card-container']")
            
            for i, card in enumerate(property_cards[:20]):  # Limiter à 20 propriétés
                try:
                    competitor_data = await self._extract_property_data(card)
                    if competitor_data and competitor_data.get('price', 0) > 0:
                        competitors.append(competitor_data)
                        
                except Exception as e:
                    logger.warning(f"Erreur lors de l'extraction de la propriété {i}: {e}")
                    continue
            
            self.competitors_cache = competitors
            self.last_analysis = datetime.now()
            
            logger.info(f"✅ {len(competitors)} concurrents trouvés")
            return competitors
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de concurrents: {e}")
            return []
    
    async def _extract_property_data(self, card_element) -> Optional[Dict]:
        """Extraire les données d'une propriété concurrente"""
        try:
            # Titre de la propriété
            title_element = card_element.find_element(By.CSS_SELECTOR, "[data-testid='listing-card-title']")
            title = title_element.text if title_element else "Titre non trouvé"
            
            # Prix par nuit
            price_element = card_element.find_element(By.CSS_SELECTOR, "[data-testid='price-availability-row']")
            price_text = price_element.text if price_element else "0"
            price = self._extract_price_from_text(price_text)
            
            # Note et nombre d'avis
            rating_element = card_element.find_element(By.CSS_SELECTOR, "[data-testid='listing-card-subtitle']")
            rating_info = rating_element.text if rating_element else ""
            rating, reviews_count = self._extract_rating_info(rating_info)
            
            # Type de logement
            property_type_element = card_element.find_element(By.CSS_SELECTOR, "[data-testid='listing-card-name']")
            property_type = property_type_element.text if property_type_element else ""
            
            # Lien vers l'annonce
            link_element = card_element.find_element(By.CSS_SELECTOR, "a")
            listing_url = link_element.get_attribute("href")
            
            # ID de l'annonce
            listing_id = self._extract_listing_id_from_url(listing_url)
            
            return {
                "id": listing_id,
                "title": title,
                "price_per_night": price,
                "rating": rating,
                "reviews_count": reviews_count,
                "property_type": property_type,
                "url": listing_url,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des données: {e}")
            return None
    
    def _build_search_url(self, location: str, property_type: str, guests: int) -> str:
        """Construire l'URL de recherche Airbnb"""
        base_url = "https://www.airbnb.fr/s"
        
        # Dates par défaut (dans 30 jours pour 7 nuits)
        checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=37)).strftime("%Y-%m-%d")
        
        params = {
            "query": location,
            "checkin": checkin,
            "checkout": checkout,
            "adults": guests,
            "room_types[]": property_type
        }
        
        # Construire l'URL avec les paramètres
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}/{location}?{param_string}"
    
    def _extract_price_from_text(self, price_text: str) -> float:
        """Extraire le prix numérique du texte"""
        # Rechercher les chiffres dans le texte
        numbers = re.findall(r'\d+', price_text.replace(',', '').replace(' ', ''))
        if numbers:
            return float(numbers[0])
        return 0.0
    
    def _extract_rating_info(self, rating_text: str) -> tuple:
        """Extraire la note et le nombre d'avis"""
        try:
            # Format typique: "4,85 (123 commentaires)"
            rating_match = re.search(r'(\d+[,\.]\d+)', rating_text)
            reviews_match = re.search(r'\((\d+)', rating_text)
            
            rating = float(rating_match.group(1).replace(',', '.')) if rating_match else 0.0
            reviews = int(reviews_match.group(1)) if reviews_match else 0
            
            return rating, reviews
        except:
            return 0.0, 0
    
    def _extract_listing_id_from_url(self, url: str) -> str:
        """Extraire l'ID de l'annonce depuis l'URL"""
        match = re.search(r'/rooms/(\d+)', url)
        if match:
            return match.group(1)
        return ""
    
    async def calculate_competitor_average(self, competitors: List[Dict] = None) -> Dict:
        """Calculer la moyenne des prix concurrents avec analyses"""
        if competitors is None:
            competitors = self.competitors_cache
        
        if not competitors:
            logger.warning("Aucun concurrent trouvé pour calculer la moyenne")
            return {
                "average_price": 0,
                "median_price": 0,
                "min_price": 0,
                "max_price": 0,
                "competitor_count": 0,
                "price_range": {"low": 0, "high": 0}
            }
        
        prices = [comp["price_per_night"] for comp in competitors if comp["price_per_night"] > 0]
        
        if not prices:
            return {
                "average_price": 0,
                "median_price": 0,
                "min_price": 0,
                "max_price": 0,
                "competitor_count": 0,
                "price_range": {"low": 0, "high": 0}
            }
        
        # Calculer les statistiques
        average_price = np.mean(prices)
        median_price = np.median(prices)
        min_price = np.min(prices)
        max_price = np.max(prices)
        
        # Calculer les percentiles pour déterminer la fourchette de prix optimale
        q25 = np.percentile(prices, 25)
        q75 = np.percentile(prices, 75)
        
        analysis = {
            "average_price": round(average_price, 2),
            "median_price": round(median_price, 2),
            "min_price": round(min_price, 2),
            "max_price": round(max_price, 2),
            "competitor_count": len(competitors),
            "price_range": {
                "low": round(q25, 2),
                "high": round(q75, 2)
            },
            "standard_deviation": round(np.std(prices), 2),
            "last_updated": datetime.now().isoformat()
        }
        
        logger.info(f"📊 Analyse concurrentielle: Prix moyen {average_price:.2f}€, Médiane {median_price:.2f}€")
        
        return analysis
    
    async def get_premium_competitors(self, min_rating: float = 4.5, min_reviews: int = 10) -> List[Dict]:
        """Filtrer les concurrents premium avec de bonnes notes"""
        premium_competitors = []
        
        for competitor in self.competitors_cache:
            if (competitor.get("rating", 0) >= min_rating and 
                competitor.get("reviews_count", 0) >= min_reviews):
                premium_competitors.append(competitor)
        
        logger.info(f"🌟 {len(premium_competitors)} concurrents premium identifiés")
        return premium_competitors
    
    async def close(self):
        """Fermer le driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None