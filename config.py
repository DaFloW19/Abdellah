import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Airbnb Configuration
    AIRBNB_EMAIL = os.getenv('AIRBNB_EMAIL')
    AIRBNB_PASSWORD = os.getenv('AIRBNB_PASSWORD')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///airbnb_pricing.db')
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Pricing Algorithm Parameters
    COMPETITOR_WEIGHT = 0.7
    OCCUPANCY_WEIGHT = 0.2
    SEASONALITY_WEIGHT = 0.1
    MIN_PROFIT_MARGIN = 0.15  # 15% minimum profit margin
    
    # Monitoring Configuration
    PRICE_UPDATE_INTERVAL = int(os.getenv('PRICE_UPDATE_INTERVAL', 3600))
    COMPETITOR_SCAN_INTERVAL = int(os.getenv('COMPETITOR_SCAN_INTERVAL', 1800))
    
    # Selenium Configuration
    SELENIUM_HEADLESS = True
    SELENIUM_TIMEOUT = 30
    
    # Geographic Configuration (à ajuster selon vos propriétés)
    DEFAULT_SEARCH_RADIUS = 2  # km
    DEFAULT_CITY = "Paris"  # À modifier selon votre localisation
    
    # Pricing Limits
    MIN_PRICE_THRESHOLD = 30  # Prix minimum en euros
    MAX_PRICE_THRESHOLD = 500  # Prix maximum en euros
    PRICE_CHANGE_LIMIT = 0.20  # Maximum 20% de changement de prix par update