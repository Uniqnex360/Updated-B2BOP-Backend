from django.apps import AppConfig
from mongoengine import connect, disconnect


class UserManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_management'
    
    def ready(self):
        disconnect(alias='default')  # Disconnect existing connection if any
        connect(
            db='user_management',
            host='localhost',
            port=27017
        )


     