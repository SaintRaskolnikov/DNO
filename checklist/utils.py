# checklist/utils.py
import json
import pkgutil

def load_disease_data(disease_slug):
    try:
        data = pkgutil.get_data("checklist", f"data/diseases/{disease_slug}.json")
        if data is None:
            return None
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        return None
