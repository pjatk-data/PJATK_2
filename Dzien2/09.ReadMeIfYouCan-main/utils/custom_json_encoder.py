import json


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Check if object has a to_dict or __dict__ method
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        # Add specific handling for DIDocumentLine if needed
        # elif isinstance(obj, DIDocumentLine):
        #     return {"some_property": obj.some_property, ...}
        # Fallback to string representation
        try:
            return str(obj)
        except:
            return f"Unserializable object of type {type(obj).__name__}"
