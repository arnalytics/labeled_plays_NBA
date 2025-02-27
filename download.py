import pandas as pd
import os
import requests
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


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