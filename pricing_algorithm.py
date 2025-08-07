import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, func
from config import Config
from models import (
    get_session, create_database, Property, Competitor, CompetitorPrice, 
    MarketAnalytics, PriceHistory, PricingRule
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PricingAlgorithm:
    def __init__(self):
        self.config = Config()
        self.engine = create_database(self.config.DATABASE_URL)
        
    def calculate_optimal_price(self, property_id, target_date=None):
        """Calcule le prix optimal pour une propriété donnée"""
        if not target_date:
            target_date = datetime.now()
            
        db_session = get_session(self.engine)
        
        try:
            # Récupérer les informations de la propriété
            property_obj = db_session.query(Property).filter_by(id=property_id).first()
            if not property_obj:
                logger.error(f"Propriété {property_id} non trouvée")
                return None
            
            # Analyser le marché des concurrents
            market_data = self.analyze_competitor_market(property_id, target_date, db_session)
            
            # Calculer le prix de base selon les concurrents
            base_price = self.calculate_competitor_based_price(market_data, property_obj)
            
            # Appliquer les ajustements saisonniers et de demande
            adjusted_price = self.apply_market_adjustments(base_price, property_obj, target_date, market_data)
            
            # Appliquer les règles de pricing personnalisées
            final_price = self.apply_custom_rules(adjusted_price, property_obj, target_date, db_session)
            
            # Valider les limites de prix
            validated_price = self.validate_price_limits(final_price, property_obj)
            
            # Sauvegarder l'analyse de marché
            self.save_market_analytics(property_id, market_data, validated_price, target_date, db_session)
            
            logger.info(f"Prix optimal calculé pour la propriété {property_id}: {validated_price}€")
            
            return {
                'property_id': property_id,
                'recommended_price': validated_price,
                'current_price': property_obj.current_price,
                'competitor_avg': market_data.get('avg_price'),
                'market_demand_score': market_data.get('demand_score'),
                'confidence_score': market_data.get('confidence_score'),
                'calculation_date': target_date,
                'price_change_needed': abs(validated_price - (property_obj.current_price or 0)) > 5
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du prix optimal: {e}")
            return None
        finally:
            db_session.close()
    
    def analyze_competitor_market(self, property_id, target_date, db_session):
        """Analyse le marché des concurrents pour une propriété"""
        try:
            # Récupérer les concurrents actifs
            competitors = db_session.query(Competitor).filter_by(
                property_id=property_id,
                is_active=True
            ).all()
            
            if not competitors:
                logger.warning(f"Aucun concurrent trouvé pour la propriété {property_id}")
                return self.get_default_market_data()
            
            # Récupérer les prix récents des concurrents (dernières 48h)
            recent_cutoff = target_date - timedelta(hours=48)
            
            competitor_prices = []
            available_competitors = 0
            
            for competitor in competitors:
                # Récupérer le prix le plus récent de ce concurrent
                latest_price = db_session.query(CompetitorPrice).filter(
                    and_(
                        CompetitorPrice.competitor_id == competitor.id,
                        CompetitorPrice.scraped_at >= recent_cutoff
                    )
                ).order_by(CompetitorPrice.scraped_at.desc()).first()
                
                if latest_price and latest_price.price:
                    # Pondérer le prix par le score de similarité
                    weighted_price = latest_price.price * competitor.similarity_score
                    competitor_prices.append({
                        'price': latest_price.price,
                        'weighted_price': weighted_price,
                        'similarity': competitor.similarity_score,
                        'available': latest_price.availability
                    })
                    
                    if latest_price.availability:
                        available_competitors += 1
            
            if not competitor_prices:
                logger.warning(f"Aucun prix concurrent récent trouvé pour la propriété {property_id}")
                return self.get_default_market_data()
            
            # Calculer les statistiques de marché
            prices = [p['price'] for p in competitor_prices]
            weighted_prices = [p['weighted_price'] for p in competitor_prices]
            similarities = [p['similarity'] for p in competitor_prices]
            
            market_data = {
                'avg_price': np.mean(prices),
                'median_price': np.median(prices),
                'min_price': np.min(prices),
                'max_price': np.max(prices),
                'weighted_avg_price': np.mean(weighted_prices),
                'total_competitors': len(competitors),
                'active_competitors': len(competitor_prices),
                'available_competitors': available_competitors,
                'avg_similarity': np.mean(similarities),
                'price_std': np.std(prices),
                'demand_score': self.calculate_demand_score(available_competitors, len(competitor_prices)),
                'confidence_score': self.calculate_confidence_score(len(competitor_prices), similarities)
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du marché: {e}")
            return self.get_default_market_data()
    
    def get_default_market_data(self):
        """Retourne des données de marché par défaut en cas d'absence de concurrents"""
        return {
            'avg_price': 100,
            'median_price': 100,
            'min_price': 80,
            'max_price': 120,
            'weighted_avg_price': 100,
            'total_competitors': 0,
            'active_competitors': 0,
            'available_competitors': 0,
            'avg_similarity': 0,
            'price_std': 20,
            'demand_score': 0.5,
            'confidence_score': 0.1
        }
    
    def calculate_demand_score(self, available_competitors, total_competitors):
        """Calcule un score de demande basé sur la disponibilité des concurrents"""
        if total_competitors == 0:
            return 0.5
        
        availability_ratio = available_competitors / total_competitors
        
        # Plus il y a de propriétés disponibles, moins la demande est forte
        demand_score = 1 - availability_ratio
        
        # Normaliser entre 0.2 et 1.0
        return max(0.2, min(1.0, demand_score))
    
    def calculate_confidence_score(self, competitor_count, similarities):
        """Calcule un score de confiance pour la recommandation de prix"""
        if competitor_count == 0:
            return 0.1
        
        # Facteurs influençant la confiance
        count_factor = min(1.0, competitor_count / 10)  # Idéalement 10+ concurrents
        similarity_factor = np.mean(similarities) if similarities else 0
        
        confidence = (count_factor * 0.6) + (similarity_factor * 0.4)
        
        return max(0.1, min(1.0, confidence))
    
    def calculate_competitor_based_price(self, market_data, property_obj):
        """Calcule le prix de base selon l'analyse des concurrents"""
        competitor_avg = market_data['weighted_avg_price']
        demand_score = market_data['demand_score']
        confidence = market_data['confidence_score']
        
        # Ajustement basé sur la demande
        demand_multiplier = 0.85 + (demand_score * 0.3)  # Entre 0.85 et 1.15
        
        # Prix de base ajusté
        base_price = competitor_avg * demand_multiplier
        
        # Si on a peu de confiance dans les données, se rapprocher du prix actuel
        if confidence < 0.5 and property_obj.current_price:
            confidence_weight = confidence * 2  # Convertir 0-0.5 vers 0-1
            base_price = (base_price * confidence_weight) + (property_obj.current_price * (1 - confidence_weight))
        
        return base_price
    
    def apply_market_adjustments(self, base_price, property_obj, target_date, market_data):
        """Applique les ajustements de marché (saisonnalité, événements, etc.)"""
        adjusted_price = base_price
        
        # Ajustement saisonnier
        seasonal_multiplier = self.get_seasonal_multiplier(target_date)
        adjusted_price *= seasonal_multiplier
        
        # Ajustement jour de la semaine
        weekday_multiplier = self.get_weekday_multiplier(target_date)
        adjusted_price *= weekday_multiplier
        
        # Ajustement basé sur la volatilité du marché
        volatility_adjustment = self.get_volatility_adjustment(market_data)
        adjusted_price *= volatility_adjustment
        
        return adjusted_price
    
    def get_seasonal_multiplier(self, target_date):
        """Retourne un multiplicateur saisonnier"""
        month = target_date.month
        
        # Multiplicateurs saisonniers pour la France (à ajuster selon la localisation)
        seasonal_factors = {
            1: 0.85,   # Janvier - basse saison
            2: 0.90,   # Février
            3: 0.95,   # Mars
            4: 1.05,   # Avril - début haute saison
            5: 1.10,   # Mai
            6: 1.15,   # Juin
            7: 1.20,   # Juillet - haute saison
            8: 1.20,   # Août - haute saison
            9: 1.10,   # Septembre
            10: 1.00,  # Octobre
            11: 0.90,  # Novembre
            12: 0.95   # Décembre - fêtes
        }
        
        return seasonal_factors.get(month, 1.0)
    
    def get_weekday_multiplier(self, target_date):
        """Retourne un multiplicateur selon le jour de la semaine"""
        weekday = target_date.weekday()  # 0 = Lundi, 6 = Dimanche
        
        # Multiplicateurs par jour (week-end plus cher)
        weekday_factors = {
            0: 0.95,   # Lundi
            1: 0.95,   # Mardi
            2: 0.95,   # Mercredi
            3: 1.00,   # Jeudi
            4: 1.05,   # Vendredi
            5: 1.10,   # Samedi
            6: 1.10    # Dimanche
        }
        
        return weekday_factors.get(weekday, 1.0)
    
    def get_volatility_adjustment(self, market_data):
        """Ajustement basé sur la volatilité des prix du marché"""
        price_std = market_data.get('price_std', 0)
        avg_price = market_data.get('avg_price', 100)
        
        if avg_price > 0:
            coefficient_variation = price_std / avg_price
            
            # Si le marché est très volatil, être plus conservateur
            if coefficient_variation > 0.3:
                return 0.95
            elif coefficient_variation > 0.2:
                return 0.98
            else:
                return 1.0
        
        return 1.0
    
    def apply_custom_rules(self, base_price, property_obj, target_date, db_session):
        """Applique les règles de pricing personnalisées"""
        try:
            # Récupérer les règles actives pour cette propriété
            rules = db_session.query(PricingRule).filter_by(
                property_id=property_obj.id,
                is_active=True
            ).order_by(PricingRule.priority.desc()).all()
            
            adjusted_price = base_price
            
            for rule in rules:
                if self.rule_applies(rule, target_date):
                    adjustment = rule.price_adjustment / 100  # Convertir pourcentage
                    adjusted_price *= (1 + adjustment)
                    logger.info(f"Règle appliquée: {rule.rule_name} (+{rule.price_adjustment}%)")
            
            return adjusted_price
            
        except Exception as e:
            logger.error(f"Erreur lors de l'application des règles: {e}")
            return base_price
    
    def rule_applies(self, rule, target_date):
        """Vérifie si une règle s'applique pour la date donnée"""
        try:
            import json
            conditions = json.loads(rule.conditions) if rule.conditions else {}
            
            # Vérifier les conditions de date
            if 'start_date' in conditions and 'end_date' in conditions:
                start_date = datetime.strptime(conditions['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(conditions['end_date'], '%Y-%m-%d')
                
                if not (start_date <= target_date <= end_date):
                    return False
            
            # Vérifier les conditions de jour de la semaine
            if 'weekdays' in conditions:
                if target_date.weekday() not in conditions['weekdays']:
                    return False
            
            # Vérifier les conditions de mois
            if 'months' in conditions:
                if target_date.month not in conditions['months']:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des règles: {e}")
            return False
    
    def validate_price_limits(self, price, property_obj):
        """Valide que le prix respecte les limites configurées"""
        # Limites absolues
        min_price = self.config.MIN_PRICE_THRESHOLD
        max_price = self.config.MAX_PRICE_THRESHOLD
        
        # Limites relatives si on a un prix actuel
        if property_obj.current_price:
            max_change = property_obj.current_price * self.config.PRICE_CHANGE_LIMIT
            relative_min = property_obj.current_price - max_change
            relative_max = property_obj.current_price + max_change
            
            min_price = max(min_price, relative_min)
            max_price = min(max_price, relative_max)
        
        # Respecter la marge minimum
        if property_obj.base_cost:
            min_profitable_price = property_obj.base_cost * (1 + self.config.MIN_PROFIT_MARGIN)
            min_price = max(min_price, min_profitable_price)
        
        # Appliquer les limites
        validated_price = max(min_price, min(max_price, price))
        
        if validated_price != price:
            logger.info(f"Prix ajusté selon les limites: {price:.2f}€ -> {validated_price:.2f}€")
        
        return round(validated_price, 2)
    
    def save_market_analytics(self, property_id, market_data, recommended_price, target_date, db_session):
        """Sauvegarde l'analyse de marché en base de données"""
        try:
            analytics = MarketAnalytics(
                property_id=property_id,
                date=target_date,
                avg_competitor_price=market_data['avg_price'],
                median_competitor_price=market_data['median_price'],
                min_competitor_price=market_data['min_price'],
                max_competitor_price=market_data['max_price'],
                total_competitors=market_data['total_competitors'],
                available_competitors=market_data['available_competitors'],
                market_demand_score=market_data['demand_score'],
                recommended_price=recommended_price,
                confidence_score=market_data['confidence_score']
            )
            
            db_session.add(analytics)
            db_session.commit()
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'analyse: {e}")
            db_session.rollback()
    
    def update_property_price(self, property_id, new_price, reason="Algorithm recommendation"):
        """Met à jour le prix d'une propriété et enregistre l'historique"""
        db_session = get_session(self.engine)
        
        try:
            property_obj = db_session.query(Property).filter_by(id=property_id).first()
            if not property_obj:
                return False
            
            old_price = property_obj.current_price
            
            # Enregistrer dans l'historique
            history_entry = PriceHistory(
                property_id=property_id,
                old_price=old_price,
                new_price=new_price,
                reason=reason
            )
            db_session.add(history_entry)
            
            # Mettre à jour le prix actuel
            property_obj.current_price = new_price
            property_obj.updated_at = datetime.now()
            
            db_session.commit()
            
            logger.info(f"Prix mis à jour pour la propriété {property_id}: {old_price}€ -> {new_price}€")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du prix: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()

if __name__ == "__main__":
    # Test de l'algorithme
    algorithm = PricingAlgorithm()
    
    # Exemple d'utilisation
    result = algorithm.calculate_optimal_price(1)
    if result:
        print(f"Prix optimal calculé: {result['recommended_price']}€")
        print(f"Confiance: {result['confidence_score']:.2f}")
        print(f"Score de demande: {result['market_demand_score']:.2f}")