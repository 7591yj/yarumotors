import fastapi
import fastf1
import os
from datetime import datetime
from typing import Optional
import httpx
from fastapi import Header, HTTPException, Depends
from pydantic import BaseModel

app = fastapi.FastAPI(
    title="YaruMotors API", description="API for the YaruMotors project"
)

fastf1.Cache.enable_cache("./cache")

API_TOKEN = os.getenv("API_TOKEN", "local-dev-token")
CDN_URL = os.getenv("CDN_URL", "http://localhost:8000/")
print(API_TOKEN)


def require_auth(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


class ManifestQuery(BaseModel):
    year: int
    event: str
    session: str
    asset: str


class SessionQuery(BaseModel):
    year: int
    event: str
    session: str


@app.get("/health")
def health_check():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/manifest")
def check_manifest(data: ManifestQuery):
    url = f"{CDN_URL}/{data.year}/{data.event}/{data.session}/{data.asset}.png"
    resp = httpx.head(url, follow_redirects=True)
    if resp.status_code == 200:
        return {"available": True, "url": url}
    elif resp.status_code == 404:
        return {"available": False, "url": url}
    raise HTTPException(status_code=resp.status_code)


@app.post("/session/generate", dependencies=[Depends(require_auth)])
def generate_asset(data: SessionQuery):
    """
    Trigger generation for a specific session
    Payload example:
      {
        "year": 2025,
        "event": "Sao Paulo",
        "session": "Race",
        "asset": "constructors"
      }
    """
    try:
        session = fastf1.get_session(data.year, data.event, data.session)
        session.load()
        if session.results is None or session.results.empty:
            return {"status": "unavailable"}
        results = session.results[["Abbreviation", "Position", "Time", "Status"]]
        return {
            "status": "ready",
            "event": f"{data.event} {data.session}",
            "results": results.to_dict(orient="records"),
        }
    except Exception as e:
        return {"status": "error", "details": str(e)}


@app.post("/cron/run", dependencies=[Depends(require_auth)])
def cron_run():
    """
    Called after sessions end
    Scans schedule or runs standard generation tasks automatically
    """
    started = datetime.now().isoformat()
    # TODO: Implement actual schedule polling
    return {"status": "ok", "started": started}
