try:
    from dotenv import load_dotenv
    load_dotenv()
    # Also try backend/.env if exists
    load_dotenv("backend/.env")
except ImportError:
    pass

import os
import boto3

aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_session_token = os.getenv("AWS_SESSION_TOKEN")
aws_region = os.getenv("AWS_REGION", "us-east-1")
bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "qwen2p5-coder-32b-instruct-v0-1")

print("=" * 60)
print("AWS BEDROCK CONNECTION TEST")
print("=" * 60)
print(f"Region:          {aws_region}")
print(f"Access Key ID:   {aws_access_key[:8]}... (length {len(aws_access_key)})" if aws_access_key else "Access Key ID:   NOT SET")
print(f"Secret Key:      {'SET' if aws_secret_key else 'NOT SET'}")
print(f"Session Token:   {'SET' if aws_session_token else 'NOT SET'}")
print(f"Model ID:        {bedrock_model_id}")
print("-" * 60)

if not aws_access_key or not aws_secret_key:
    print("[WARNING] AWS credentials not found in environment or .env file.")
    print("To enable AWS Bedrock:")
    print("1. Create a .env file in the project root or backend/ folder with:")
    print("   AWS_ACCESS_KEY_ID=your_key")
    print("   AWS_SECRET_ACCESS_KEY=your_secret")
    print("   AWS_REGION=us-east-1 (or your region)")
    print("   BEDROCK_MODEL_ID=your_model_id")
    print("2. The pipeline will automatically use AWS Bedrock when credentials are present,")
    print("   and fall back to deterministic RAG / local LLM when unavailable.")
else:
    try:
        kwargs = {
            "region_name": aws_region,
            "aws_access_key_id": aws_access_key,
            "aws_secret_access_key": aws_secret_key,
        }
        if aws_session_token:
            kwargs["aws_session_token"] = aws_session_token
            
        client = boto3.client("bedrock", **kwargs)
        models = client.list_foundation_models()
        model_count = len(models.get("modelSummaries", []))
        print(f"[OK] AWS Bedrock connection successful! ({model_count} foundation models available)")
    except Exception as e:
        print(f"[ERROR] AWS Bedrock connection failed: {type(e).__name__} - {e}")
print("=" * 60)

