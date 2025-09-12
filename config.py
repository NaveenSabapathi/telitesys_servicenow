# import os
# from dotenv import load_dotenv
#
# load_dotenv()  # Load .env contents
# # ; SQLALCHEMY_DATABASE_URI=postgresql://postgres:12345@localhost/breeze
#
# class Config:
#     SECRET_KEY = os.getenv("SECRET_KEY", "e7dJMW8ixOEzEtf0K4fg2hz2BNl1oyk4E9Pp2iGWRVc")
#     SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
#     print("Ssssssssssssssssss")
#     print(SQLALCHEMY_DATABASE_URI)
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
#     SESSION_COOKIE_SECURE = True
#     SESSION_COOKIE_HTTPONLY = True
#     SESSION_COOKIE_SAMESITE = "Lax"
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env contents
print("✅ .env file loaded")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "e7dJMW8ixOEzEtf0K4fg2hz2BNl1oyk4E9Pp2iGWRVc")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "postgresql://neondb_owner:npg_9doPOBkLnMY8@ep-frosty-sound-a8p439ik-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 2
    }

    SESSION_COOKIE_SECURE = False ##local setup needs false
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


# Debug logging
print("🔐 Loaded SECRET_KEY:", Config.SECRET_KEY[:4] + "..." if Config.SECRET_KEY else "❌ Not set")
print("🔗 Loaded SQLALCHEMY_DATABASE_URI:", Config.SQLALCHEMY_DATABASE_URI)
