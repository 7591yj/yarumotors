import fastapi
import fastf1
import os
from datetime import datetime
from typing import Optional
import httpx
from fastapi import Header, HTTPException, Depends, UploadFile
from pydantic import BaseModel
import boto3
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
import io
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from timple.timedelta import strftimedelta

import fastf1
import fastf1.plotting
from fastf1.core import Laps

load_dotenv(".env")

app = fastapi.FastAPI(
    title="YaruMotors API", description="API for the YaruMotors project"
)

r2 = boto3.client(
    "s3",
    region_name="auto",
    endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
)
BUCKET = os.getenv("R2_BUCKET")

fastf1.Cache.enable_cache("./cache")

API_TOKEN = os.getenv("API_TOKEN", "local-dev-token")
CDN_URL = os.getenv("CDN_URL", "http://localhost:8000/")


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


# TODO: REMOVE
@app.get("/download/{filename}")
async def download_file(filename: str):
    obj = r2.get_object(Bucket=BUCKET, Key=filename)
    stream = io.BytesIO(obj["Body"].read())
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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


@app.post("/session/race/generate", dependencies=[Depends(require_auth)])
def generate_race_asset(data: SessionQuery):
    """
    Trigger generation for a specific session
    Payload example:
      {
        "year": 2025,
        "event": "Sao Paulo",
      }
    """
    try:
        session = fastf1.get_session(data.year, data.event, "R")
        session.load()
        if session.results is None or session.results.empty:
            return {"status": "unavailable"}
        results = session.results[["Abbreviation", "Position", "Time", "Status"]]
        return {
            "status": "ready",
            "event": f"{data.event} Race",
            "results": results.to_dict(orient="records"),
        }
    except Exception as e:
        return {"status": "error", "details": str(e)}


@app.post("/session/qualifying/generate", dependencies=[Depends(require_auth)])
def generate_qualifying_asset(data: SessionQuery):
    """
    Trigger generation for a qualifying session result
    Payload example:
      {
        "year": 2025,
        "event": "Sao Paulo",
      }
    """
    try:
        session = fastf1.get_session(data.year, data.event, "Q")
        session.load()
        if session.results is None or session.results.empty:
            return {"status": "unavailable"}
        drivers = pd.unique(session.laps["Driver"])
        list_fastest_laps = list()
        for drv in drivers:
            drvs_fastest_lap = session.laps.pick_drivers(drv).pick_fastest()
            list_fastest_laps.append(drvs_fastest_lap)
        fastest_laps = (
            Laps(list_fastest_laps).sort_values(by="LapTime").reset_index(drop=True)
        )
        pole_lap = fastest_laps.pick_fastest()
        fastest_laps["LapTimeDelta"] = fastest_laps["LapTime"] - pole_lap["LapTime"]
        team_colors = list()
        for index, lap in fastest_laps.iterlaps():
            color = fastf1.plotting.get_team_color(lap["Team"], session=session)
            team_colors.append(color)

        fig, ax = plt.subplots()
        ax.barh(
            fastest_laps.index,
            fastest_laps["LapTimeDelta"],
            color=team_colors,
            edgecolor="grey",
        )
        ax.set_yticks(fastest_laps.index)
        ax.set_yticklabels(fastest_laps["Driver"])

        # show fastest at the top
        ax.invert_yaxis()

        # draw vertical lines behind the bars
        ax.set_axisbelow(True)
        ax.xaxis.grid(True, which="major", linestyle="--", color="black", zorder=-1000)

        lap_time_string = strftimedelta(pole_lap["LapTime"], "%m:%s.%ms")

        plt.suptitle(
            f"{session.event['EventName']} {session.event.year} Qualifying\n"
            f"Fastest Lap: {lap_time_string} ({pole_lap['Driver']})"
        )

        # save the plot to a buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        r2.upload_fileobj(buf, BUCKET, f"{data.year}/{data.event}/qualifying.png")
        file_url = f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com/{BUCKET}/{data.year}/{data.event}/qualifying.png"
        buf.close()

        return {
            "status": "ready",
            "url": file_url,
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
