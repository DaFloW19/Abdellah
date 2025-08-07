import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

logger = logging.getLogger(__name__)

Base = declarative_base()

class PriceHistory(Base):
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    current_price = Column(Float)
    recommended_price = Column(Float)
    competitor_average = Column(Float)
    competitor_count = Column(Integer)
    confidence = Column(Float)
    reasoning = Column(Text)

class PriceMonitor:
    """Service principal de surveillance et de gestion automatique des prix"""
    
    def __init__(self, airbnb_client, competitor_analyzer, pricing_algorithm):
        self.airbnb_client = airbnb_client
        self.competitor_analyzer = competitor_analyzer
        self.pricing_algorithm = pricing_algorithm
        
        self.is_monitoring = False
        self.last_check = None
        self.start_time = None
        self.update_interval = int(os.getenv("UPDATE_INTERVAL_MINUTES", 30))
        
        # Base de données
        database_url = os.getenv("DATABASE_URL", "sqlite:///airbnb_pricing.db")
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Cache des données actuelles
        self.current_data = {
            "competitor_average": 0,
            "recommended_price": 0,
            "current_price": 0,
            "competitors": [],
            "last_update": ""
        }
    
    async def start_monitoring(self):
        """Démarrer la surveillance continue"""
        if self.is_monitoring:
            logger.warning("La surveillance est déjà active")
            return
        
        self.is_monitoring = True
        self.start_time = datetime.now()
        
        logger.info(f"🚀 Démarrage de la surveillance automatique (intervalle: {self.update_interval} min)")
        
        # Première analyse immédiate
        await self._perform_analysis()
        
        # Boucle de surveillance
        while self.is_monitoring:
            try:
                await asyncio.sleep(self.update_interval * 60)  # Convertir en secondes
                await self._perform_analysis()
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance: {e}")
                await asyncio.sleep(60)  # Attendre 1 minute avant de retry
    
    async def stop_monitoring(self):
        """Arrêter la surveillance"""
        self.is_monitoring = False
        logger.info("🛑 Surveillance arrêtée")
    
    async def _perform_analysis(self):
        """Effectuer une analyse complète des prix"""
        try:
            logger.info("🔄 Début de l'analyse des prix...")
            self.last_check = datetime.now()
            
            # 1. Se connecter à Airbnb et récupérer les annonces
            await self.airbnb_client.login()
            listings = await self.airbnb_client.get_listings()
            
            if not listings:
                logger.warning("Aucune annonce trouvée")
                return
            
            # Analyser la première annonce (peut être étendu pour plusieurs)
            main_listing = listings[0]
            current_price = main_listing.get("current_price", 0)
            
            # 2. Rechercher les concurrents (utiliser la localisation de l'annonce)
            # Pour cette démo, utiliser une localisation générique
            location = "Paris, France"  # À adapter selon l'annonce
            competitors = await self.competitor_analyzer.find_competitors(location)
            
            # 3. Calculer les statistiques concurrentielles
            competitor_stats = await self.competitor_analyzer.calculate_competitor_average(competitors)
            
            # 4. Calculer le prix optimal
            # Simuler des données de qualité (à récupérer de l'annonce réelle)
            listing_quality = {
                "rating": 4.5,  # À récupérer de l'annonce
                "reviews_count": 25  # À récupérer de l'annonce
            }
            
            pricing_result = self.pricing_algorithm.calculate_optimal_price(
                competitor_data=competitor_stats,
                current_price=current_price,
                listing_quality=listing_quality
            )
            
            # 5. Sauvegarder dans l'historique
            await self._save_to_history(current_price, pricing_result, competitor_stats)
            
            # 6. Mettre à jour le cache
            self.current_data.update({
                "competitor_average": competitor_stats.get("average_price", 0),
                "recommended_price": pricing_result.get("recommended_price", 0),
                "current_price": current_price,
                "competitors": competitors[:10],  # Limiter à 10 pour l'affichage
                "last_update": datetime.now().isoformat(),
                "pricing_details": pricing_result,
                "competitor_stats": competitor_stats
            })
            
            # 7. Mise à jour automatique du prix si activée
            await self._auto_update_price_if_needed(pricing_result)
            
            logger.info(f"✅ Analyse terminée - Prix recommandé: {pricing_result.get('recommended_price', 0)}€")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse: {e}")
    
    async def _save_to_history(self, current_price: float, pricing_result: Dict, competitor_stats: Dict):
        """Sauvegarder les données dans l'historique"""
        try:
            history_entry = PriceHistory(
                current_price=current_price,
                recommended_price=pricing_result.get("recommended_price", 0),
                competitor_average=competitor_stats.get("average_price", 0),
                competitor_count=competitor_stats.get("competitor_count", 0),
                confidence=pricing_result.get("confidence", 0),
                reasoning=pricing_result.get("reasoning", "")
            )
            
            self.session.add(history_entry)
            self.session.commit()
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
            self.session.rollback()
    
    async def _auto_update_price_if_needed(self, pricing_result: Dict):
        """Mise à jour automatique du prix si les conditions sont remplies"""
        try:
            recommended_price = pricing_result.get("recommended_price", 0)
            current_price = pricing_result.get("current_price", 0)
            confidence = pricing_result.get("confidence", 0)
            price_change = abs(recommended_price - current_price)
            
            # Conditions pour la mise à jour automatique
            min_confidence = 70  # Confiance minimale
            min_change = 5      # Changement minimal en euros
            max_change = 50     # Changement maximal en euros
            
            should_update = (
                confidence >= min_confidence and
                price_change >= min_change and
                price_change <= max_change
            )
            
            if should_update:
                logger.info(f"🔄 Mise à jour automatique du prix: {current_price}€ -> {recommended_price}€")
                success = await self.airbnb_client.update_listing_price(new_price=recommended_price)
                
                if success:
                    logger.info(f"✅ Prix mis à jour automatiquement")
                    # Mettre à jour le prix actuel dans le cache
                    self.current_data["current_price"] = recommended_price
                else:
                    logger.warning("❌ Échec de la mise à jour automatique")
            else:
                logger.info(f"ℹ️ Pas de mise à jour automatique (confiance: {confidence}%, changement: {price_change}€)")
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour automatique: {e}")
    
    async def get_current_data(self) -> Dict:
        """Récupérer les données actuelles pour l'API"""
        return self.current_data.copy()
    
    async def get_price_history(self, days: int = 30) -> List[Dict]:
        """Récupérer l'historique des prix"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            history = self.session.query(PriceHistory)\
                .filter(PriceHistory.timestamp >= cutoff_date)\
                .order_by(PriceHistory.timestamp.desc())\
                .limit(100)\
                .all()
            
            result = []
            for entry in history:
                result.append({
                    "timestamp": entry.timestamp.isoformat(),
                    "current_price": entry.current_price,
                    "recommended_price": entry.recommended_price,
                    "competitor_average": entry.competitor_average,
                    "competitor_count": entry.competitor_count,
                    "confidence": entry.confidence,
                    "reasoning": entry.reasoning
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique: {e}")
            return []
    
    async def force_analysis(self):
        """Forcer une nouvelle analyse"""
        logger.info("🔄 Analyse forcée demandée")
        await self._perform_analysis()
        return await self.get_current_data()
    
    async def get_competitor_details(self) -> List[Dict]:
        """Récupérer les détails des concurrents"""
        return self.competitor_analyzer.competitors_cache
    
    async def get_pricing_trends(self, days: int = 7) -> Dict:
        """Analyser les tendances de prix"""
        try:
            history = await self.get_price_history(days)
            
            if len(history) < 2:
                return {"trend": "insufficient_data"}
            
            # Calculer la tendance des prix recommandés
            recent_prices = [h["recommended_price"] for h in history[:7]]
            older_prices = [h["recommended_price"] for h in history[7:14]] if len(history) > 7 else recent_prices
            
            recent_avg = sum(recent_prices) / len(recent_prices) if recent_prices else 0
            older_avg = sum(older_prices) / len(older_prices) if older_prices else recent_avg
            
            trend_direction = "stable"
            trend_percentage = 0
            
            if recent_avg > older_avg * 1.05:
                trend_direction = "increasing"
                trend_percentage = ((recent_avg - older_avg) / older_avg) * 100
            elif recent_avg < older_avg * 0.95:
                trend_direction = "decreasing"
                trend_percentage = ((older_avg - recent_avg) / older_avg) * 100
            
            return {
                "trend": trend_direction,
                "percentage": round(trend_percentage, 2),
                "recent_average": round(recent_avg, 2),
                "previous_average": round(older_avg, 2),
                "analysis_period": days
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des tendances: {e}")
            return {"trend": "error", "message": str(e)}
    
    def __del__(self):
        """Nettoyage lors de la destruction de l'objet"""
        if hasattr(self, 'session'):
            self.session.close()