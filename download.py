import pandas as pd
import os
import requests
import cv2
import glob
import re

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from tqdm import tqdm


###################################################################################################
'''
    DOWNLOAD VIDEOS FROM THE NBA SERVER ONCE WE HAVE THE LINKS SCRAPED
'''
###################################################################################################

def download_video(video_url, file_name):
    """
    Descarga un vídeo desde una URL y lo guarda con el nombre especificado.
    """
    try:
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        with open(file_name, 'wb') as video_file:
            for chunk in response.iter_content(chunk_size=8192):
                video_file.write(chunk)
    except Exception as e:
        print(f"Error al descargar {file_name}: {e}")
        

def download_videos_from_dataframe(df: pd.DataFrame, output_dir: str, max_workers: int = 8):
    """
    Descarga los vídeos de la columna 'Video Link' en paralelo y los guarda con el nombre de 'PLAY ID'.
    
    Args:
        df (pd.DataFrame): DataFrame con los enlaces de vídeo en la columna 'Video Link' y 'PLAY ID'.
        output_dir (str): Directorio donde se guardarán los vídeos.
        max_workers (int): Número máximo de hilos para la descarga en paralelo.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Preparar tareas para descargar los vídeos
    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, row in df.iterrows():
            video_url = row['Video Link']
            play_id = row['PLAY ID']
            file_name = os.path.join(output_dir, f"{play_id}.mp4")  # Nombre basado en 'PLAY ID'
            tasks.append(executor.submit(download_video, video_url, file_name))
        
        # Mostrar barra de progreso
        for future in tqdm(tasks, desc="Descargando vídeos"):
            future.result()

###################################################################################################
'''
    EXTRACT THE FRAMES FROM THE VIDEOS AND SAVE THEM INTO FOLDERS
'''
###################################################################################################

def extract_frames_from_video(video_path, frames_dir, target_fps=None, target_resolution=None):
    """
    Extract frames from a single video file with specified FPS and resolution.
    
    Args:
        video_path (str): Path to the video file
        frames_dir (str): Directory where to save extracted frames
        target_fps (float, optional): Target frames per second to extract. 
                                    If None, extracts all frames.
        target_resolution (tuple, optional): Target resolution as (width, height).
                                          If None, uses original resolution.
    
    Returns:
        tuple: (video_name, frame_count) - The name of the processed video and number of frames extracted
    """
    # Extract the video name without extension
    video_name = os.path.basename(video_path).split('.')[0]
    
    # Create directory for this video's frames
    video_frames_dir = os.path.join(frames_dir, video_name)
    os.makedirs(video_frames_dir, exist_ok=True)
    
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return video_name, 0
    
    # Get original video properties
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Calculate frame extraction interval if target_fps is specified
    if target_fps and target_fps < original_fps:
        frame_interval = original_fps / target_fps
    else:
        frame_interval = 1  # Extract every frame
    
    frame_count = 0
    frame_idx = 0
    
    while True:
        # Read a frame
        ret, frame = cap.read()
        
        # Break if no frame was read (end of video)
        if not ret:
            break
        
        # Only process frames according to the target FPS
        if frame_idx % frame_interval < 1.0:
            # Resize the frame if target resolution is specified
            if target_resolution:
                frame = cv2.resize(frame, target_resolution)
            
            # Save the frame
            frame_path = os.path.join(video_frames_dir, f"frame_{frame_count:04d}.jpg")
            cv2.imwrite(frame_path, frame)
            
            frame_count += 1
        
        frame_idx += 1
    
    cap.release()

    return video_name, frame_count


def extract_frames_from_videos(videos_dir, max_workers=None, target_fps=None, target_resolution=None, skip_existing=True):
    """
    Extract frames from videos named 'hoop_cut_x.mp4' in the specified directory using parallel processing.
    With capability to resume from a specific video if the process was interrupted.
    
    Args:
        videos_dir (str): Directory containing the videos
        max_workers (int, optional): Maximum number of worker processes. 
                                   If None, uses the number of processors on the machine.
        target_fps (float, optional): Target frames per second to extract.
                                    If None, extracts all frames.
        target_resolution (tuple, optional): Target resolution as (width, height).
                                          If None, uses original resolution.
        skip_existing (bool): If True, skips videos that already have frame folders.
    """

    # Create frames directory if it doesn't exist
    parent_dir = os.path.dirname(videos_dir)
    
    frames_dir = os.path.join(parent_dir, 'frames')
    os.makedirs(frames_dir, exist_ok=True)
    
    # Get all video files matching the pattern
    video_pattern = os.path.join(videos_dir, 'hoop_cut_*.mp4')
    all_video_files = glob.glob(video_pattern)
    
    # Sort videos by their numeric index to ensure consistent processing order
    def extract_number(filename):
        match = re.search(r'hoop_cut_(\d+)\.mp4', filename)
        if match:
            return int(match.group(1))
        return 0
    
    all_video_files.sort(key=extract_number)
    
    # Filter videos for processing
    video_files = []
    
    for video_path in all_video_files:
        video_name = os.path.basename(video_path).split('.')[0]
        video_frames_dir = os.path.join(frames_dir, video_name)
        
        # Skip already processed videos if skip_existing is True
        if skip_existing and os.path.exists(video_frames_dir) and len(os.listdir(video_frames_dir)) > 0:
            print(f"Skipping {video_name} - frames already exist")
            continue
        
        video_files.append(video_path)
    
    if not video_files:
        print("No videos to process - either all are completed or none match the resume criteria.")
        return
        
    print(f"Found {len(all_video_files)} total videos, processing {len(video_files)} videos")
    
    if target_fps is not None:
        print(f"Target FPS: {target_fps}")
    if target_resolution is not None:
        print(f"Target resolution: {target_resolution[0]}x{target_resolution[1]}")
    
    # Process videos in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_video = {
            executor.submit(
                extract_frames_from_video, 
                video_path, 
                frames_dir, 
                target_fps, 
                target_resolution
            ): video_path for video_path in video_files
        }
        
        # Process as they complete with a progress bar
        for future in tqdm(as_completed(future_to_video), total=len(video_files), desc="Extracting frames"):
            video_path = future_to_video[future]
            try:
                video_name, frame_count = future.result()
            except Exception as exc:
                print(f"{video_path} generated an exception: {exc}")


if __name__ == "__main__":
    # Specify the relative directory containing your videos
    videos_directory = 'HoopCut_net/dataset'
    
    # You can specify max_workers if needed, otherwise it will use all available CPU cores
    extract_frames_from_videos(
        videos_directory, 
        target_fps=30, 
        target_resolution=(640, 360),
        skip_existing=True  # Skip videos that have already been processed
    )
    print("Frame extraction complete!")
