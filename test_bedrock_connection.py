#!/usr/bin/env python
"""
Test AWS Bedrock connection with credentials from .env
"""

from dotenv import load_dotenv
import os
import boto3

# Load environment variables from .env
load_dotenv()

# Get credentials from .env
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION", "us-east-1")

print(f"AWS Configuration:")
print(f"  Region: {aws_region}")
print(f"  Access Key ID: {aws_access_key[:10]}..." if aws_access_key else "  Access Key ID: NOT SET")
print(f"  Secret Key: {'SET' if aws_secret_key else 'NOT SET'}")

try:
    # Create Bedrock client with explicit region
    client = boto3.client(
        'bedrock-runtime',
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    
    print("\n✓ AWS Bedrock connection successful!")
    print(f"✓ Ready to use model: {os.getenv('BEDROCK_MODEL_ID')}")
    
except Exception as e:
    print(f"\n✗ Connection failed: {type(e).__name__}")
    print(f"✗ Error: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Check AWS_ACCESS_KEY_ID in .env file")
    print("2. Check AWS_SECRET_ACCESS_KEY in .env file")
    print("3. Verify credentials have Bedrock permissions")
    print("4. Check if AWS region is correct (current: {})".format(aws_region))
