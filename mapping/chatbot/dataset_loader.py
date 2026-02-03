import pandas as pd

def load_chatbot_dataset():
    def load(file):
        return pd.read_excel(file).fillna("").to_dict(orient="records")

    return {
        "facialwash": load("dataset/Chatbot/FACIAL WASH ALL BRAND.xlsx"),
        "toner": load("dataset/Chatbot/TONER ALL BRAND.xlsx"),
        "serum": load("dataset/Chatbot/SERUM ALL BRAND.xlsx"),
        "moisturizer": load("dataset/Chatbot/MOISTURIZER ALL BRAND.xlsx"),
        "sunscreen": load("dataset/Chatbot/SUNSCREEN ALL BRAND.xlsx"),
    }
