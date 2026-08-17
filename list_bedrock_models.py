#!/usr/bin/env python
"""
List all available Bedrock models in your account
"""

import boto3
from dotenv import load_dotenv
import os

load_dotenv()

aws_region = os.getenv("AWS_REGION", "us-east-1")

print(f"Listing models in region: {aws_region}\n")

client = boto3.client('bedrock', region_name=aws_region)

try:
    response = client.list_foundation_models()
    
    # Filter for Qwen models
    qwen_models = [m for m in response['modelSummaries'] if 'qwen' in m['modelId'].lower()]
    
    print("=" * 80)
    print("QWEN MODELS AVAILABLE:")
    print("=" * 80)
    
    if qwen_models:
        for model in qwen_models:
            print(f"\nModel ID: {model['modelId']}")
            print(f"  Provider: {model.get('provider', 'N/A')}")
            print(f"  Name: {model.get('modelName', 'N/A')}")
            print(f"  Input tokens: {model.get('inputTokenCount', 'N/A')}")
            print(f"  Output tokens: {model.get('outputTokenCount', 'N/A')}")
    else:
        print("\nNo Qwen models found in your region!")
        print("Available models in this region:")
        for model in response['modelSummaries'][:10]:
            print(f"  - {model['modelId']}")
        if len(response['modelSummaries']) > 10:
            print(f"  ... and {len(response['modelSummaries']) - 10} more")
    
    print("\n" + "=" * 80)
    print("ALL FOUNDATION MODELS IN ACCOUNT:")
    print("=" * 80)
    for model in response['modelSummaries']:
        print(f"  {model['modelId']}")

except Exception as e:
    print(f"Error: {e}")
    print("\nMake sure your AWS credentials are set correctly in .env")
