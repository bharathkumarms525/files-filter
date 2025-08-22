# main.py
import os
import datetime
import shutil
from fastapi import FastAPI, Form, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

class FilterRequest(BaseModel):
    source_folder: str
    from_timestamp: str
    to_timestamp: str
    file_formats: str
    use_created_time: bool = False
    dest_folder_base: str
    dest_folder_name: str

def filter_files(folder_path, from_timestamp, to_timestamp, file_formats, use_created_time=False):
    """
    Recursively filter files in a folder (including subfolders) 
    based on timestamp range and multiple formats.
    """
    try:
        from_dt = datetime.datetime.strptime(from_timestamp, "%Y-%m-%d %H:%M:%S")
        to_dt = datetime.datetime.strptime(to_timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid timestamp format. Use 'YYYY-MM-DD HH:MM:SS'"
        )

    # Normalize formats
    file_formats = [fmt.strip().lower().lstrip(".") for fmt in file_formats.split(",") if fmt.strip()]

    if not file_formats:
        raise HTTPException(
            status_code=400,
            detail="No valid file formats provided"
        )

    matching_files = []

    # Walk through all subdirectories
    for root, _, files in os.walk(folder_path):
        for filename in files:
            ext = filename.split(".")[-1].lower()
            if ext in file_formats:
                file_path = os.path.join(root, filename)

                # Choose timestamp type
                timestamp = os.path.getctime(file_path) if use_created_time else os.path.getmtime(file_path)
                file_time = datetime.datetime.fromtimestamp(timestamp)

                if from_dt <= file_time <= to_dt:
                    matching_files.append(file_path)

    return matching_files

@app.get("/", response_class=HTMLResponse)
async def get_form():
    with open("static/index.html") as f:
        return f.read()

@app.post("/filter-and-copy")
async def filter_and_copy(
    source_folder: str = Form(...),
    from_timestamp: str = Form(...),
    to_timestamp: str = Form(...),
    file_formats: str = Form(...),
    use_created_time: bool = Form(False),
    dest_folder_base: str = Form(...),
    dest_folder_name: str = Form(...)
):
    # Validate source folder
    if not os.path.isdir(source_folder):
        raise HTTPException(
            status_code=400,
            detail=f"Source folder does not exist or is not a directory: {source_folder}"
        )
    
    # Validate destination base folder
    if not os.path.isdir(dest_folder_base):
        raise HTTPException(
            status_code=400,
            detail=f"Destination base folder does not exist: {dest_folder_base}"
        )
    
    # Create destination folder
    dest_folder = os.path.join(dest_folder_base, dest_folder_name)
    os.makedirs(dest_folder, exist_ok=True)
    
    # Filter files
    try:
        matching_files = filter_files(
            source_folder,
            from_timestamp,
            to_timestamp,
            file_formats,
            use_created_time
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
    # Copy files to destination
    copied_files = []
    for src in matching_files:
        try:
            filename = os.path.basename(src)
            dest_path = os.path.join(dest_folder, filename)
            shutil.copy2(src, dest_path)
            copied_files.append(dest_path)
        except Exception as e:
            # Continue copying other files even if one fails
            continue
    
    return {
        "status": "success",
        "count": len(copied_files),
        "destination_folder": dest_folder,
        "copied_files": copied_files,
        "skipped_files": len(matching_files) - len(copied_files)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)