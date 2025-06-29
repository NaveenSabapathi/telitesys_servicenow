import os
from dotenv import load_dotenv

load_dotenv()  # Load .env contents

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "e7dJMW8ixOEzEtf0K4fg2hz2BNl1oyk4E9Pp2iGWRVc")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
