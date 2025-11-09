import fastapi
from datetime import datetime
from typing import Optional
import httpx
from fastapi import Header, HTTPException, Depends
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import io
import matplotlib
from html2image import Html2Image

from utils import notify_bot

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from timple.timedelta import strftimedelta

import fastf1
import fastf1.plotting
from fastf1.core import Laps
from fastf1.ergast import Ergast

from app.config import APP_TITLE, APP_DESCRIPTION
from app.config import (
    API_TOKEN,
    CDN_URL,
    BOT_DOMAIN,
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET,
    R2_ENDPOINT,
    r2,
)
from app.config import CACHE_DIR

app = fastapi.FastAPI(title=APP_TITLE, description=APP_DESCRIPTION)

# ------------------  CONFIG  ------------------

TEAM_LOGOS = {
    "mclaren": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/mclaren/2025mclarenlogowhite.webp",
    "red_bull": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/redbullracing/2025redbullracinglogowhite.webp",
    "ferrari": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/ferrari/2025ferrarilogowhite.webp",
    "mercedes": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/mercedes/2025mercedeslogowhite.webp",
    "williams": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/williams/2025williamslogowhite.webp",
    "aston_martin": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/astonmartin/2025astonmartinlogowhite.webp",
    "haas": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/haas/2025haaslogowhite.webp",
    "alpine": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/alpine/2025alpinelogowhite.webp",
    "sauber": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/kicksauber/2025kicksauberlogowhite.webp",
    "rb": "https://media.formula1.com/image/upload/c_lfill,w_48/q_auto/v1740000000/common/f1/2025/rb/2025rblogowhite.webp",
}

TEAM_COLORS = {
    "mclaren": "#FF8000",
    "red_bull": "#1E41FF",
    "ferrari": "#DC0000",
    "mercedes": "#00D2BE",
    "williams": "#005AFF",
    "aston_martin": "#006F62",
    "haas": "#B6BABD",
    "alpine": "#2293D1",
    "sauber": "#52E252",
    "rb": "#6692FF",
}

FALLBACK_COLOR = "#D0D0D0"  # neutral gray

# ---------------------------------------------


def generate_row(entry):
    constructor = entry["constructorIds"][0]
    name = f"{entry['givenName']} {entry['familyName']}"
    logo = TEAM_LOGOS.get(constructor, "")
    color = TEAM_COLORS.get(constructor, "#444")
    html = f"""
      <div class="row" style="background:{color};">
      <span class="pos">{entry["position"]}</span>
        <img class="logo" src="{logo}" alt="{constructor}">
        <span class="name">{name}</span>
        <span class="points">{entry["points"]} pts</span>
      </div>
    """
    return html


def generate_html(standings):
    rows = [generate_row(e) for e in standings]
    body_rows = "\n".join(rows)

    html = f"""
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: white;
      margin: 0;
      padding: 20px;
    }}
    .row {{
      display: flex;
      align-items: center;
      padding: 6px 12px;
      margin-bottom: 4px;
      border-radius: 6px;
    }}
    .pos {{
      width: 28px;
      font-weight: bold;
      text-align: right;
      margin-right: 10px;
    }}
    .logo {{
      width: 28px;
      height: 28px;
      margin-right: 10px;
      object-fit: contain;
    }}
    .name {{
      font-weight: 600;
      font-size: 14px;
    }}
    .points {{
      margin-left: auto;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  {body_rows}
</body>
</html>
"""
    return html


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
    obj = r2.get_object(Bucket=R2_BUCKET, Key=filename)
    stream = io.BytesIO(obj["Body"].read())
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/worker-update")
def worker_update():
    result = notify_bot.notify_bot(BOT_DOMAIN)
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


@app.post("/generate/driverstanding/current", dependencies=[Depends(require_auth)])
def generate_driver_standing_asset():
    try:
        ergast = Ergast(result_type="pandas", auto_cast=True)
        standing = ergast.get_driver_standings(season="current")

        description = standing.description.to_dict(orient="records")
        standings_df = standing.content[0]
        standings_data = standings_df.to_dict(orient="records")

        hti = Html2Image()
        htu_output = generate_html(standings_data)
        hti = Html2Image(size=(500, 1100))
        hti.screenshot(html_str=htu_output, save_as="f1_standings.png")

        return {"description": description, "standings": standings_data}
    except Exception as e:
        return {"error": str(e)}


@app.post("/generate/constructorstanding/current", dependencies=[Depends(require_auth)])
def generate_constructor_standing_asset():
    try:
        ergast = Ergast(result_type="pandas", auto_cast=True)
        standing = ergast.get_constructor_standings(season="current")

        description = standing.description.to_dict(orient="records")
        standings_df = standing.content[0]
        standings_data = standings_df.to_dict(orient="records")

        return {"description": description, "standings": standings_data}
    except Exception as e:
        return {"error": str(e)}


@app.post("/generate/session/race/", dependencies=[Depends(require_auth)])
def generate_race_asset(data: SessionQuery):
    """
    Trigger generation for a race session result
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


@app.post("/generate/session/sprint/", dependencies=[Depends(require_auth)])
def generate_sprint_asset(data: SessionQuery):
    """
    Trigger generation for a sprint session result
    Payload example:
      {
        "year": 2025,
        "event": "Sao Paulo",
      }
    """
    try:
        session = fastf1.get_session(data.year, data.event, "Sprint")
        session.load()
        if session.results is None or session.results.empty:
            return {"status": "unavailable"}
        results = session.results[["Abbreviation", "Position", "Time", "Status"]]
        return {
            "status": "ready",
            "event": f"{data.event} Sprint",
            "results": results.to_dict(orient="records"),
        }
    except Exception as e:
        return {"status": "error", "details": str(e)}


@app.post("/generate/session/qualifying", dependencies=[Depends(require_auth)])
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
        r2.upload_fileobj(buf, R2_BUCKET, f"{data.year}/{data.event}/qualifying.png")
        file_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{R2_BUCKET}/{data.year}/{data.event}/qualifying.png"
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
