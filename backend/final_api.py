"""Local scientific pipeline jobs. Delivered results also work as a static website."""
from __future__ import annotations

import importlib.util
import importlib.metadata
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "FINAL" / "code"
JOBS = ROOT / "artifacts" / "final-jobs"
router = APIRouter(prefix="/api/final", tags=["MODIS to VIIRS"])
LOCK = threading.RLock()
PROCESSES: dict[str, subprocess.Popen] = {}
ACTIVE: str | None = None
DEPENDENCIES = {"pandas": "pandas", "numpy": "numpy", "scipy": "scipy", "scikit-learn": "sklearn",
                "pyproj": "pyproj", "matplotlib": "matplotlib", "openpyxl": "openpyxl", "pyarrow": "pyarrow"}


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country: Literal["Malaysia", "Indonesia"] = "Malaysia"
    profile: Literal["features", "validation", "full"] = "full"
    trees: Literal[200, 800] = 200
    tune: bool = False
    download: bool = False


def require_local_origin(request: Request):
    origin = request.headers.get("origin")
    if origin:
        host = urlparse(origin).hostname
        local = {"localhost", "127.0.0.1", "::1"}
        if host != request.url.hostname and not (host in local and request.url.hostname in local):
            raise HTTPException(403, "Pipeline commands must come from this website.")


def job_dir(job_id: str) -> Path:
    if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise HTTPException(404, "Unknown pipeline run.")
    path = JOBS / job_id
    if not (path / "status.json").exists():
        raise HTTPException(404, "Unknown pipeline run.")
    return path


def save(path: Path, state: dict):
    # Readers and writers share LOCK; replace avoids half-written job state.
    with LOCK:
        tmp = path / "status.tmp"
        tmp.write_text(json.dumps(state), encoding="utf-8")
        tmp.replace(path / "status.json")


def read(path: Path) -> dict:
    with LOCK:
        return json.loads((path / "status.json").read_text(encoding="utf-8"))


def missing_dependencies():
    return [package for package, module in DEPENDENCIES.items() if importlib.util.find_spec(module) is None]


def execute(job_id: str, options: RunRequest):
    global ACTIVE
    path = JOBS / job_id
    state = read(path)
    raw = CODE / "data" / "raw"
    try:
        (path / "output").mkdir(parents=True, exist_ok=True)
        (path / "output" / "environment.json").write_text(json.dumps({"python": sys.version,
            "packages": {package: importlib.metadata.version(package) for package in DEPENDENCIES},
            "options": options.model_dump()}, indent=2), encoding="utf-8")
        if options.download:
            raw = path / "raw"
            if options.country == "Malaysia":
                shutil.copytree(CODE / "data" / "raw", raw)
        steps = {"features": "features", "validation": "features,loyo", "full": "features,loyo,sim,calendar"}[options.profile]
        command = [sys.executable, "-u", str(CODE / "run_all.py"), "--country", options.country,
                   "--raw", str(raw), "--work", str(path / "work"), "--out", str(path / "output"),
                   "--trees", str(options.trees), "--steps", steps]
        if not options.tune:
            command.append("--quick")
        if options.download:
            command.append("--download")
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "MPLCONFIGDIR": str(path / "matplotlib")}
        with (path / "run.log").open("w", encoding="utf-8") as log:
            def run(cmd):
                with LOCK:
                    if read(path)["status"] == "cancelled":
                        return -1
                    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                            start_new_session=os.name != "nt")
                    PROCESSES[job_id] = proc
                code = proc.wait()
                with LOCK:
                    PROCESSES.pop(job_id, None)
                return code

            code = run(command)
            if code == 0 and options.profile == "full":
                state = read(path)
                if state["status"] != "cancelled":
                    state["stage"] = "Preparing website data"
                    save(path, state)
                    code = run([sys.executable, "-u", str(ROOT / "scripts" / "build_final_data.py"),
                                "--country", options.country, "--raw", str(raw), "--results", str(path / "output"),
                                "--work", str(path / "work"), "--dest", str(path / "bundle")])
        state = read(path)
        if state["status"] != "cancelled":
            state.update(status="complete" if code == 0 else "failed", stage="Finished" if code == 0 else "Failed",
                         return_code=code, finished=datetime.now(timezone.utc).isoformat())
            if code == 0 and (path / "bundle" / "manifest.json").exists():
                state["bundle"] = f"/api/final/jobs/{job_id}/bundle/"
            save(path, state)
    except Exception as exc:
        state = read(path)
        if state["status"] != "cancelled":
            state.update(status="failed", stage="Failed", error=str(exc), finished=datetime.now(timezone.utc).isoformat())
            save(path, state)
    finally:
        with LOCK:
            PROCESSES.pop(job_id, None)
            if ACTIVE == job_id:
                ACTIVE = None


@router.get("/status")
def status():
    missing = missing_dependencies()
    return {"available": CODE.exists() and not missing, "missing_dependencies": missing, "active": ACTIVE,
            "countries": ["Malaysia", "Indonesia"], "profiles": ["features", "validation", "full"]}


@router.post("/jobs", status_code=202)
def start(options: RunRequest, request: Request):
    global ACTIVE
    require_local_origin(request)
    if not CODE.exists() or missing_dependencies():
        raise HTTPException(503, {"message": "Install the scientific requirements and include FINAL/code.", "missing": missing_dependencies()})
    if options.country != "Malaysia" and not options.download:
        raise HTTPException(422, "Indonesia requires Download FIRMS inputs; only Malaysia's inputs are bundled.")
    with LOCK:
        if ACTIVE:
            raise HTTPException(409, {"message": "A scientific run is already in progress.", "job_id": ACTIVE})
        job_id = uuid.uuid4().hex
        path = JOBS / job_id
        path.mkdir(parents=True)
        state = {"id": job_id, "status": "running", "stage": "Starting", "options": options.model_dump(),
                 "started": datetime.now(timezone.utc).isoformat()}
        save(path, state)
        ACTIVE = job_id
        threading.Thread(target=execute, args=(job_id, options), daemon=True).start()
        return state


@router.get("/jobs/{job_id}")
def job(job_id: str):
    path = job_dir(job_id)
    state = read(path)
    if state["status"] == "running" and ACTIVE != job_id:
        state.update(status="interrupted", stage="Server restarted; start a new run")
    log = path / "run.log"
    if log.exists():
        with log.open("rb") as stream:
            stream.seek(max(0, log.stat().st_size - 40000))
            state["log"] = stream.read().decode("utf-8", errors="replace")
    else:
        state["log"] = "Starting the scientific pipeline…"
    if state["status"] == "running":
        lines = [line for line in state["log"].splitlines() if line.startswith("===== ")]
        if lines and state["stage"] != "Preparing website data":
            state["stage"] = lines[-1].strip("= ")
    output = path / "output"
    state["files"] = [{"name": p.relative_to(output).as_posix(), "bytes": p.stat().st_size,
                       "url": f"/api/final/jobs/{job_id}/files/{p.relative_to(output).as_posix()}"}
                      for p in sorted(output.rglob("*")) if p.is_file()] if output.exists() else []
    return state


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str, request: Request):
    require_local_origin(request)
    path = job_dir(job_id)
    with LOCK:
        state = read(path)
        if state["status"] != "running" or ACTIVE != job_id:
            raise HTTPException(409, "This run is no longer running.")
        state.update(status="cancelled", stage="Cancelled", finished=datetime.now(timezone.utc).isoformat())
        save(path, state)
        if job_id in PROCESSES:
            proc = PROCESSES[job_id]
            if proc.poll() is None:
                if os.name == "nt":
                    # A venv launcher can own a second Python process on Windows.
                    # Terminate the owned job tree, including that child interpreter.
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
    return state


def safe_file(base: Path, name: str):
    target = (base / name).resolve()
    if not target.is_relative_to(base.resolve()) or not target.is_file():
        raise HTTPException(404, "File not found.")
    return target


@router.get("/jobs/{job_id}/files/{name:path}")
def result_file(job_id: str, name: str):
    target = safe_file(job_dir(job_id) / "output", name)
    return FileResponse(target, filename=target.name)


@router.get("/jobs/{job_id}/bundle/{name:path}")
def bundle_file(job_id: str, name: str):
    path = job_dir(job_id)
    state = read(path)
    if state["status"] != "complete" or "bundle" not in state:
        raise HTTPException(409, "Website data are available after the complete pipeline finishes.")
    return FileResponse(safe_file(path / "bundle", name))
