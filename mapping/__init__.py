# =====================================================
# MAPPING PACKAGE INIT (FINAL - CLEAN & SIDANG READY)
# =====================================================

# ========================
# Chatbot Core Logic
# ========================
from mapping.chatbot.chatbot_logic import (
    chatbot_logic,
    handle_chat,
    clean_text
)

# ========================
# Ingredient Mapping
# ========================
from mapping.ingredient_mapping.ingredient_info import INGREDIENT_INFO
from mapping.ingredient_mapping.ingredient_synonyms import INGREDIENT_SYNONYMS

# ========================
# Ingredient Rules
# ========================
from mapping.ingredient_rules.ingredient_interactions import INGREDIENT_INTERACTIONS

# ========================
# Keyword / Mapping Files
# ========================
from mapping.problem_mapping import PROBLEM_KEYWORDS
from mapping.product_mapping import PRODUCT_MAP
from mapping.skin_mapping import SKIN_TYPES

# =====================================================
# Exported symbols (PUBLIC API)
# =====================================================
__all__ = [
    # chatbot
    "chatbot_logic",
    "handle_chat",
    "clean_text",

    # ingredient
    "INGREDIENT_INFO",
    "INGREDIENT_SYNONYMS",
    "INGREDIENT_INTERACTIONS",

    # mappings
    "PROBLEM_KEYWORDS",
    "PRODUCT_MAP",
    "SKIN_TYPES"
]
