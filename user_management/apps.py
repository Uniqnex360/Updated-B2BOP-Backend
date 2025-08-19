#from django.apps import AppConfig
#from mongoengine import connect, disconnect


#class UserManagementConfig(AppConfig):
#    default_auto_field = 'django.db.models.BigAutoField'
#    name = 'user_management'
#    
#    def ready(self):
#        disconnect(alias='default')  # Disconnect existing connection if any
#        connect(
#            db='user_management',
#            host='localhost',
#            port=27017
#        )


     





from django.apps import AppConfig
from mongoengine import connect, disconnect
import os                              # ✅ ADD this import
class UserManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_management'
    
    def ready(self):
        disconnect(alias='default')  # Disconnect existing connection if any
        
        # ✅ REPLACE the connect() section with this:
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/user_management')
        
        try:
            connect(host=mongo_uri)
            print(f"✅ Connected to MongoDB successfully")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")