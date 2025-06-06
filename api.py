import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from utils import detect_platform, download_video_with_progress, save_video_to_cache, get_cached_video

app = FastAPI()

@app.get("/download")
async def download_video(url: str = Query(..., description="Посилання на відео")):
    platform = detect_platform(url)
    if not platform:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    cached = get_cached_video(url)
    if cached:
        return FileResponse(cached, media_type="video/mp4", filename=os.path.basename(cached))

    filename = await download_video_with_progress(url)
    if not filename:
        raise HTTPException(status_code=500, detail="Download failed")

    cached_path = save_video_to_cache(url, filename)
    return FileResponse(cached_path, media_type="video/mp4", filename=os.path.basename(cached_path))