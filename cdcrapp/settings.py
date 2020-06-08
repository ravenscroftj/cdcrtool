import os
from dotenv import load_dotenv

load_dotenv()


#SECURITY_URL_PREFIX="/api/security"
SECRET_KEY = os.environ.get("SECRET_KEY", "changeme")
TEMPLATES_AUTO_RELOAD = True
SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", "supersecretsalt")
SQLALCHEMY_POOL_RECYCLE = os.environ.get("SQLALCHEMY_POOL_RECYCLE",30)
WTF_CSRF_ENABLED = False