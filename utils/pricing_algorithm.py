import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math

logger = logging.getLogger(__name__)

class PricingAlgorithm:
    """Algorithme intelligent pour calculer le prix optimal basé sur l'analyse concurrentielle"""
    
    def __init__(self):
        self.base_margin = 0.05  # Marge de base de 5%
        self.max_margin = 0.15   # Marge maximale de 15%
        self.min_margin = -0.05  # Marge minimale (peut être négative pour être compétitif)
        
        # Facteurs de pondération
        self.weights = {
            "competitor_average": 0.4,
            "premium_average": 0.3,
            "seasonal_factor": 0.15,
            "occupancy_factor": 0.15
        }
    
    def calculate_optimal_price(self, 
                               competitor_data: Dict,
                               current_price: float,
                               listing_quality: Dict = None,
                               seasonal_data: Dict = None,
                               occupancy_rate: float = None) -> Dict:
        """
        Calculer le prix optimal basé sur plusieurs facteurs
        
        Args:
            competitor_data: Données d'analyse concurrentielle
            current_price: Prix actuel de l'annonce
            listing_quality: Données de qualité de l'annonce (note, avis, etc.)
            seasonal_data: Données saisonnières
            occupancy_rate: Taux d'occupation actuel
        
        Returns:
            Dict contenant le prix recommandé et les détails du calcul
        """
        try:
            logger.info("🧮 Calcul du prix optimal en cours...")
            
            if not competitor_data or competitor_data.get("competitor_count", 0) == 0:
                logger.warning("Données concurrentielles insuffisantes")
                return {
                    "recommended_price": current_price,
                    "price_change": 0,
                    "confidence": 0,
                    "reasoning": "Données concurrentielles insuffisantes"
                }
            
            # 1. Prix de base basé sur la concurrence
            base_price = self._calculate_competitive_base_price(competitor_data)
            
            # 2. Ajustements pour la qualité de l'annonce
            quality_multiplier = self._calculate_quality_multiplier(listing_quality)
            
            # 3. Ajustements saisonniers
            seasonal_multiplier = self._calculate_seasonal_multiplier(seasonal_data)
            
            # 4. Ajustements pour le taux d'occupation
            occupancy_multiplier = self._calculate_occupancy_multiplier(occupancy_rate)
            
            # 5. Calcul du prix final
            calculated_price = base_price * quality_multiplier * seasonal_multiplier * occupancy_multiplier
            
            # 6. Appliquer les limites de marge
            final_price = self._apply_margin_limits(calculated_price, competitor_data["average_price"])
            
            # 7. Arrondir à l'euro le plus proche
            recommended_price = round(final_price)
            
            # 8. Calculer la confiance de la recommandation
            confidence = self._calculate_confidence(competitor_data, listing_quality)
            
            # 9. Générer l'explication
            reasoning = self._generate_reasoning(
                base_price, quality_multiplier, seasonal_multiplier, 
                occupancy_multiplier, competitor_data
            )
            
            price_change = recommended_price - current_price
            change_percentage = (price_change / current_price * 100) if current_price > 0 else 0
            
            result = {
                "recommended_price": recommended_price,
                "current_price": current_price,
                "price_change": price_change,
                "change_percentage": round(change_percentage, 2),
                "confidence": confidence,
                "reasoning": reasoning,
                "factors": {
                    "base_price": round(base_price, 2),
                    "quality_multiplier": round(quality_multiplier, 3),
                    "seasonal_multiplier": round(seasonal_multiplier, 3),
                    "occupancy_multiplier": round(occupancy_multiplier, 3)
                },
                "competitor_stats": competitor_data,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Prix optimal calculé: {recommended_price}€ (variation: {price_change:+.0f}€)")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du prix optimal: {e}")
            return {
                "recommended_price": current_price,
                "price_change": 0,
                "confidence": 0,
                "reasoning": f"Erreur de calcul: {str(e)}"
            }
    
    def _calculate_competitive_base_price(self, competitor_data: Dict) -> float:
        """Calculer le prix de base basé sur l'analyse concurrentielle"""
        average_price = competitor_data.get("average_price", 0)
        median_price = competitor_data.get("median_price", 0)
        
        # Utiliser la médiane si elle est significativement différente de la moyenne
        # (indique une distribution asymétrique des prix)
        if abs(average_price - median_price) / average_price > 0.2:
            base_price = median_price
            logger.info(f"📊 Utilisation de la médiane comme prix de base: {base_price}€")
        else:
            base_price = average_price
            logger.info(f"📊 Utilisation de la moyenne comme prix de base: {base_price}€")
        
        return base_price
    
    def _calculate_quality_multiplier(self, listing_quality: Dict = None) -> float:
        """Calculer le multiplicateur basé sur la qualité de l'annonce"""
        if not listing_quality:
            return 1.0
        
        rating = listing_quality.get("rating", 4.0)
        reviews_count = listing_quality.get("reviews_count", 0)
        
        # Multiplicateur basé sur la note (4.0-5.0 -> 0.95-1.15)
        rating_multiplier = 0.75 + (rating / 5.0) * 0.4
        
        # Multiplicateur basé sur le nombre d'avis (plus d'avis = plus de confiance)
        if reviews_count >= 50:
            reviews_multiplier = 1.05
        elif reviews_count >= 20:
            reviews_multiplier = 1.02
        elif reviews_count >= 5:
            reviews_multiplier = 1.0
        else:
            reviews_multiplier = 0.98  # Pénalité pour peu d'avis
        
        multiplier = rating_multiplier * reviews_multiplier
        
        # Limiter entre 0.9 et 1.2
        multiplier = max(0.9, min(1.2, multiplier))
        
        logger.info(f"🌟 Multiplicateur qualité: {multiplier:.3f} (note: {rating}, avis: {reviews_count})")
        return multiplier
    
    def _calculate_seasonal_multiplier(self, seasonal_data: Dict = None) -> float:
        """Calculer le multiplicateur saisonnier"""
        if not seasonal_data:
            # Utiliser un multiplicateur basique basé sur la date actuelle
            return self._get_basic_seasonal_multiplier()
        
        demand_level = seasonal_data.get("demand_level", "normal")
        
        multipliers = {
            "very_high": 1.25,
            "high": 1.15,
            "normal": 1.0,
            "low": 0.9,
            "very_low": 0.8
        }
        
        multiplier = multipliers.get(demand_level, 1.0)
        logger.info(f"📅 Multiplicateur saisonnier: {multiplier:.3f} (demande: {demand_level})")
        return multiplier
    
    def _get_basic_seasonal_multiplier(self) -> float:
        """Multiplicateur saisonnier basique basé sur le mois"""
        current_month = datetime.now().month
        
        # Multiplicateurs basés sur la saisonnalité générale en France
        seasonal_multipliers = {
            1: 0.85,   # Janvier - faible
            2: 0.90,   # Février - faible
            3: 0.95,   # Mars - moyen-faible
            4: 1.05,   # Avril - moyen-élevé
            5: 1.10,   # Mai - élevé
            6: 1.20,   # Juin - très élevé
            7: 1.25,   # Juillet - pic
            8: 1.25,   # Août - pic
            9: 1.15,   # Septembre - élevé
            10: 1.05,  # Octobre - moyen-élevé
            11: 0.90,  # Novembre - faible
            12: 0.95   # Décembre - moyen (fêtes)
        }
        
        return seasonal_multipliers.get(current_month, 1.0)
    
    def _calculate_occupancy_multiplier(self, occupancy_rate: float = None) -> float:
        """Calculer le multiplicateur basé sur le taux d'occupation"""
        if occupancy_rate is None:
            return 1.0
        
        # Logique: taux d'occupation élevé = augmenter prix, faible = baisser prix
        if occupancy_rate >= 0.9:
            multiplier = 1.1   # Très forte demande
        elif occupancy_rate >= 0.8:
            multiplier = 1.05  # Forte demande
        elif occupancy_rate >= 0.6:
            multiplier = 1.0   # Demande normale
        elif occupancy_rate >= 0.4:
            multiplier = 0.95  # Demande faible
        else:
            multiplier = 0.9   # Très faible demande
        
        logger.info(f"🏠 Multiplicateur occupation: {multiplier:.3f} (taux: {occupancy_rate*100:.1f}%)")
        return multiplier
    
    def _apply_margin_limits(self, calculated_price: float, competitor_average: float) -> float:
        """Appliquer les limites de marge par rapport à la concurrence"""
        min_price = competitor_average * (1 + self.min_margin)
        max_price = competitor_average * (1 + self.max_margin)
        
        limited_price = max(min_price, min(max_price, calculated_price))
        
        if limited_price != calculated_price:
            logger.info(f"🚫 Prix limité: {calculated_price:.2f}€ -> {limited_price:.2f}€")
        
        return limited_price
    
    def _calculate_confidence(self, competitor_data: Dict, listing_quality: Dict = None) -> float:
        """Calculer le niveau de confiance de la recommandation (0-100)"""
        confidence = 50  # Base
        
        # Confiance basée sur le nombre de concurrents
        competitor_count = competitor_data.get("competitor_count", 0)
        if competitor_count >= 15:
            confidence += 25
        elif competitor_count >= 10:
            confidence += 20
        elif competitor_count >= 5:
            confidence += 15
        elif competitor_count >= 3:
            confidence += 10
        else:
            confidence -= 20
        
        # Confiance basée sur la cohérence des prix concurrents
        std_dev = competitor_data.get("standard_deviation", 0)
        avg_price = competitor_data.get("average_price", 1)
        if avg_price > 0:
            cv = std_dev / avg_price  # Coefficient de variation
            if cv < 0.2:
                confidence += 15  # Prix cohérents
            elif cv > 0.5:
                confidence -= 15  # Prix très dispersés
        
        # Confiance basée sur la qualité des données de l'annonce
        if listing_quality:
            reviews_count = listing_quality.get("reviews_count", 0)
            if reviews_count >= 20:
                confidence += 10
            elif reviews_count < 5:
                confidence -= 10
        
        return max(0, min(100, confidence))
    
    def _generate_reasoning(self, base_price: float, quality_mult: float, 
                           seasonal_mult: float, occupancy_mult: float, 
                           competitor_data: Dict) -> str:
        """Générer une explication de la recommandation de prix"""
        explanations = []
        
        # Prix de base
        explanations.append(f"Prix de base: {base_price:.0f}€ (basé sur {competitor_data.get('competitor_count', 0)} concurrents)")
        
        # Ajustements qualité
        if quality_mult > 1.05:
            explanations.append(f"Majoration de {(quality_mult-1)*100:.1f}% pour la qualité supérieure")
        elif quality_mult < 0.95:
            explanations.append(f"Réduction de {(1-quality_mult)*100:.1f}% pour améliorer la compétitivité")
        
        # Ajustements saisonniers
        if seasonal_mult > 1.05:
            explanations.append(f"Majoration saisonnière de {(seasonal_mult-1)*100:.1f}%")
        elif seasonal_mult < 0.95:
            explanations.append(f"Réduction saisonnière de {(1-seasonal_mult)*100:.1f}%")
        
        # Ajustements d'occupation
        if occupancy_mult > 1.02:
            explanations.append(f"Majoration de {(occupancy_mult-1)*100:.1f}% (forte demande)")
        elif occupancy_mult < 0.98:
            explanations.append(f"Réduction de {(1-occupancy_mult)*100:.1f}% (faible demande)")
        
        return " | ".join(explanations)
    
    def get_price_recommendations_by_period(self, competitor_data: Dict, 
                                           current_price: float,
                                           days_ahead: int = 30) -> List[Dict]:
        """Obtenir des recommandations de prix pour les prochaines périodes"""
        recommendations = []
        
        for day in range(0, days_ahead, 7):  # Recommandations hebdomadaires
            future_date = datetime.now() + timedelta(days=day)
            
            # Simuler des données saisonnières pour cette date
            seasonal_data = {
                "demand_level": self._predict_demand_level(future_date)
            }
            
            recommendation = self.calculate_optimal_price(
                competitor_data=competitor_data,
                current_price=current_price,
                seasonal_data=seasonal_data
            )
            
            recommendation["date"] = future_date.strftime("%Y-%m-%d")
            recommendation["week_of_year"] = future_date.isocalendar()[1]
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _predict_demand_level(self, date: datetime) -> str:
        """Prédire le niveau de demande pour une date donnée"""
        month = date.month
        weekday = date.weekday()  # 0=lundi, 6=dimanche
        
        # Logique simplifiée de prédiction
        if month in [7, 8]:  # Juillet, Août
            return "very_high"
        elif month in [6, 9]:  # Juin, Septembre
            return "high"
        elif month in [4, 5, 10]:  # Avril, Mai, Octobre
            return "normal"
        elif month in [12, 3]:  # Décembre, Mars
            return "low"
        else:  # Janvier, Février, Novembre
            return "very_low"