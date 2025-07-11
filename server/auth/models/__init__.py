"""Auth models package."""

# Import all models from the models.py file to make them available
# when importing from server.auth.models
from server.auth.models import *

# Also make email_events models available
from .email_events import *