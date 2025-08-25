"""Application configuration values.

The values below are loaded from environment variables when available to make
the application easily configurable without modifying the source code. The
defaults are only meant for development and should be replaced in production.
"""

import os

# Public API keys -----------------------------------------------------------------
# These keys are read from environment variables so they can be changed without
# touching the code base. Replace the default values with your own keys.

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "72ffaa246beb41a1af6d772997996e32")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "0beb33baf383caabcb53cca61f1a04b8")

# Base URL for the currency exchange API. The URL already contains the API key.
# Override ``CURRENCY_API_URL`` in the environment to use a different service or
# key.
CURRENCY_API_URL = os.getenv(
    "CURRENCY_API_URL",
    "https://v6.exchangerate-api.com/v6/adc5a7aa933d9a8382bb47d5/latest/USD",
)

