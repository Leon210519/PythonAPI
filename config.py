"""Application configuration values.

All values are sourced from environment variables to keep secrets out of the
code base. Set the variables listed below before running the application.
"""

import os

# Public API keys -----------------------------------------------------------------
NEWS_API_KEY = os.environ["NEWS_API_KEY"]
WEATHER_API_KEY = os.environ["WEATHER_API_KEY"]
CURRENCY_API_KEY = os.environ["CURRENCY_API_KEY"]

