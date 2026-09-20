import json
import os

import boto3
from dotenv import load_dotenv


load_dotenv()


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "google.gemma-3-27b-it"
)

MAX_TOKENS = int(
    os.getenv("MAX_TOKENS", "1024")
)

TEMPERATURE = float(
    os.getenv("TEMPERATURE", "0.0")
)


bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION
)


def generate_answer(
    question: str,
    context: str
) -> str:

    prompt = f"""
You are an AI assistant working inside a persistent document workspace.

Answer the user's question using ONLY the provided document context.

Rules:
1. Do not invent information.
2. If the answer is not available in the context, say:
   "I could not find enough information in the uploaded documents."
3. Keep the answer concise and factual.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:
"""

    request_body = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
    }

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(request_body),
        contentType="application/json",
        accept="application/json"
    )

    response_body = json.loads(
        response["body"].read()
    )

    return response_body["choices"][0]["message"]["content"]