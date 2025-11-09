from dotenv import load_dotenv

load_dotenv(".env")

APP_TITLE = "Yarumotors API"
APP_DESCRIPTION = "API for the Yarumotors project"

import os

API_TOKEN = os.getenv("API_TOKEN", "local-dev-token")
CDN_URL = os.getenv("CDN_URL", "http://localhost:8000/")
BOT_DOMAIN = os.getenv("BOT_DOMAIN", "https://yarumotors.subdomain.workers.dev/")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
CACHE_DIR = "./cache"

import boto3

r2 = boto3.client(
    "s3",
    region_name="auto",
    endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
)

import fastf1

fastf1.Cache.enable_cache("./cache")
