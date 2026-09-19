"""
ZOEY — config.py
Every constant lives here. Nothing else in the project should hardcode
wake words, model names, mic settings, or personality text.

API keys are loaded from a .env file (see .env.example) so you don't
have to re-export them every terminal session.
"""
*pls request this file,this contain personal information. thanks

BRAIN_TEMPERATURE = _float_env("BRAIN_TEMPERATURE", 0.25 if OFFLINE_MODE else 0.65)
BRAIN_TOP_P = float(os.environ.get("BRAIN_TOP_P", "0.90"))
