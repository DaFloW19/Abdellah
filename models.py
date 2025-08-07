from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

class Property(Base):
    __tablename__ = 'properties'
    
    id = Column(Integer, primary_key=True)
    airbnb_id = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    address = Column(String(300))
    latitude = Column(Float)
    longitude = Column(Float)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    max_guests = Column(Integer)
    property_type = Column(String(100))
    current_price = Column(Float)
    base_cost = Column(Float)  # Coût de base pour calculer la marge
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    price_history = relationship("PriceHistory", back_populates="property")
    competitors = relationship("Competitor", back_populates="property")

class Competitor(Base):
    __tablename__ = 'competitors'
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    airbnb_id = Column(String(50), nullable=False)
    title = Column(String(200))
    distance_km = Column(Float)
    similarity_score = Column(Float)  # Score de similarité avec notre propriété
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    max_guests = Column(Integer)
    property_type = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    property = relationship("Property", back_populates="competitors")
    price_data = relationship("CompetitorPrice", back_populates="competitor")

class PriceHistory(Base):
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    old_price = Column(Float)
    new_price = Column(Float)
    reason = Column(String(200))  # Raison du changement de prix
    algorithm_recommendation = Column(Float)
    competitor_avg_price = Column(Float)
    occupancy_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    property = relationship("Property", back_populates="price_history")

class CompetitorPrice(Base):
    __tablename__ = 'competitor_prices'
    
    id = Column(Integer, primary_key=True)
    competitor_id = Column(Integer, ForeignKey('competitors.id'), nullable=False)
    price = Column(Float, nullable=False)
    date_for = Column(DateTime, nullable=False)  # Date pour laquelle le prix est valable
    availability = Column(Boolean, default=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    competitor = relationship("Competitor", back_populates="price_data")

class PricingRule(Base):
    __tablename__ = 'pricing_rules'
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    rule_name = Column(String(100), nullable=False)
    rule_type = Column(String(50))  # 'seasonal', 'event', 'occupancy', 'competitor'
    conditions = Column(Text)  # JSON avec les conditions
    price_adjustment = Column(Float)  # Ajustement en pourcentage
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)  # Priorité d'application de la règle
    created_at = Column(DateTime, default=datetime.utcnow)

class MarketAnalytics(Base):
    __tablename__ = 'market_analytics'
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    avg_competitor_price = Column(Float)
    median_competitor_price = Column(Float)
    min_competitor_price = Column(Float)
    max_competitor_price = Column(Float)
    total_competitors = Column(Integer)
    available_competitors = Column(Integer)
    market_demand_score = Column(Float)  # Score de demande basé sur la disponibilité
    recommended_price = Column(Float)
    confidence_score = Column(Float)  # Confiance dans la recommandation
    created_at = Column(DateTime, default=datetime.utcnow)

# Fonctions utilitaires pour la base de données
def create_database(database_url):
    """Crée la base de données et toutes les tables"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    """Retourne une nouvelle session de base de données"""
    Session = sessionmaker(bind=engine)
    return Session()