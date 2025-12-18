from decimal import Decimal
import json
from django.core.serializers.json import DjangoJSONEncoder

class DecimalJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)