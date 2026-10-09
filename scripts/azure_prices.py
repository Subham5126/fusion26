"""Read public Microsoft Retail Prices; no authentication or resources are changed."""
import argparse
import json
from pathlib import Path
import httpx

parser = argparse.ArgumentParser()
parser.add_argument('--region', default='centralindia')
parser.add_argument('--output', type=Path, default=Path('.cache/azure-v1/retail-prices.json'))
args = parser.parse_args()
items = []
with httpx.Client(timeout=60) as client:
    for service in ('Azure Container Apps', 'Container Registry'):
        url = 'https://prices.azure.com/api/retail/prices'
        params = {'$filter': f"serviceName eq '{service}' and armRegionName eq '{args.region}' and priceType eq 'Consumption'"}
        while url:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            items.extend({key: item.get(key) for key in ('serviceName', 'productName', 'skuName', 'meterName',
                'armRegionName', 'retailPrice', 'unitOfMeasure', 'currencyCode', 'effectiveStartDate')} for item in data['Items'])
            url, params = data.get('NextPageLink'), None
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(items, indent=2))
print(json.dumps(items, indent=2))
