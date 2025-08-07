from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class PriceHistory(Base):
    """Modèle pour l'historique des prix"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    listing_id = Column(String(50))
    current_price = Column(Float)
    recommended_price = Column(Float)
    competitor_average = Column(Float)
    competitor_median = Column(Float)
    competitor_count = Column(Integer)
    confidence = Column(Float)
    reasoning = Column(Text)
    auto_updated = Column(Boolean, default=False)

class CompetitorData(Base):
    """Modèle pour les données des concurrents"""
    __tablename__ = 'competitor_data'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    competitor_id = Column(String(50))
    title = Column(String(200))
    price_per_night = Column(Float)
    rating = Column(Float)
    reviews_count = Column(Integer)
    property_type = Column(String(100))
    location = Column(String(200))
    url = Column(Text)

class SystemSettings(Base):
    """Modèle pour les paramètres du système"""
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True)
    value = Column(String(500))
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.now)

def init_db():
    """Initialiser la base de données"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///airbnb_pricing.db")
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    # Créer une session pour insérer les paramètres par défaut
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Paramètres par défaut
    default_settings = [
        {
            "key": "auto_update_enabled",
            "value": "true",
            "description": "Activer la mise à jour automatique des prix"
        },
        {
            "key": "min_confidence_threshold",
            "value": "70",
            "description": "Seuil de confiance minimum pour la mise à jour automatique"
        },
        {
            "key": "max_price_change",
            "value": "50",
            "description": "Changement de prix maximum autorisé en euros"
        },
        {
            "key": "update_interval_minutes",
            "value": "30",
            "description": "Intervalle de mise à jour en minutes"
        }
    ]
    
    for setting in default_settings:
        existing = session.query(SystemSettings).filter_by(key=setting["key"]).first()
        if not existing:
            new_setting = SystemSettings(
                key=setting["key"],
                value=setting["value"],
                description=setting["description"]
            )
            session.add(new_setting)
    
    try:
        session.commit()
    except:
        session.rollback()
    finally:
        session.close()
    
    return engine

def get_session():
    """Obtenir une session de base de données"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///airbnb_pricing.db")
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()