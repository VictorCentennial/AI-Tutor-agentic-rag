from google.generativeai import configure, list_models
import os
from dotenv import load_dotenv
load_dotenv()

configure(api_key=os.getenv("GOOGLE_API_KEY"))

available_models = list_models()
print([model.name for model in available_models])
