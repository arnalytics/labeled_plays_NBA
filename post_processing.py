import pandas as pd

def clean_missing_video_data(df: pd.DataFrame):
    """
    Elimina las filas que tienen el vídeo missing.
    """
    # Filtrar las filas donde 'Video Link' no es igual a la URL de video faltante
    df_cleaned = df[df['Video Link'] != 'https://videos.nba.com/nba/static/missing.mp4']
    
    return df_cleaned