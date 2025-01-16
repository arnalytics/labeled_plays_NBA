from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import bs4 as BeautifulSoup
import os
import requests
import concurrent.futures
import re
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


def initialize_driver(season: str='2023-24'):

    if season not in ['2024-25', '2023-24', '2022-23', '2021-22', '2020-21', '2019-20',  
                      '2018-19', '2017-18', '2016-17', '2015-16', '2014-15']:
        
        raise Exception("Video-data not available for this season")

    # Initialize the Chrome driver
    driver = webdriver.Chrome()

    # Navigate to the player statistics page
    driver.get("https://www.nba.com/stats/players/traditional")

    # Explicit wait to ensure the table is loaded
    time.sleep(3)

    accept_cookies(driver)
    time.sleep(3)

    # Select season
    dropdown_season_xpath = '//*[@id="__next"]/div[2]/div[2]/div[3]/section[1]/div/div/div[1]/label/div/select'
    dropdown_element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, dropdown_season_xpath))
    )
    select = Select(dropdown_element)
    select.select_by_value(season)

    # Explicit wait to ensure the table is loaded
    time.sleep(3)

    return driver


# Accept cookies
def accept_cookies(driver):
    try:
        cookie_accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]'))
        )
        cookie_accept_button.click()  # Click on 'Accept'
        print("Cookies banner closed.")
    except Exception as e:
        print("No cookies banner found or other issue:", e)


def clean_missing_video_data(df: pd.DataFrame):
    """
    Elimina las filas que tienen el vídeo missing.
    """
    # Filtrar las filas donde 'Video Link' no es igual a la URL de video faltante
    df_cleaned = df[df['Video Link'] != 'https://videos.nba.com/nba/static/missing.mp4']
    
    return df_cleaned


def count_rows_table_plays(driver, table_xpath: str):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )
        
        # Encuentra todas las filas de la tabla
        rows = driver.find_elements(By.XPATH, f"{table_xpath}/tr")
        
        # Cuenta el número de filas
        rows_number = len(rows)
    except Exception as e:
        rows_number = 45
        print(f"Error al contar las filas: {e}")

    return rows_number


def extract_assist_info(play_description: str):
    # Patrón para capturar el nombre del jugador sin el número antes de "AST"
    pattern = r"\(([^0-9()]+) \d+ AST\)"
    
    # Buscar el patrón en la cadena
    match = re.search(pattern, play_description)
    
    if match:
        # Extraer el nombre del jugador antes de "AST"
        player_name = match.group(1).strip()
        return True, player_name  # AST presente con nombre del jugador
    else:
        return False, None  # No hay AST


def create_dataframe(df_type: str = 'FGA'):
    """
    Crea un DataFrame con las columnas apropiadas según el tipo de estadísticas proporcionado.
    
    df_type: str
        Tipo de estadística para determinar las columnas del DataFrame. 
        Ejemplo: ['FGA', 'OREB', 'DREB, 'BLK']
    """

    # Diccionario con las columnas por tipo
    columns_by_type = {
        'FGA': [
            ' ', 'PLAYER', 'PLAY TYPE', 'MADE', 'SHOT TYPE', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE',
            'PERIOD', 'TIME REMAINING', 'SHOT DISTANCE (FT)', 'TEAM', 'AST', 'Assisted by', 'Video Link'
        ],
        'OREB': [
            ' ', 'PLAYER', 'PLAY DESCRIPTION', 'REBOUND TYPE', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE', 'PERIOD', 'Video Link'
        ],
        'DREB': [
            ' ', 'PLAYER', 'PLAY DESCRIPTION', 'REBOUND TYPE', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE', 'PERIOD', 'Video Link'
        ],
        'BLK': [
            ' ', 'PLAYER', 'PLAY DESCRIPTION', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE', 'PERIOD', 'Video Link'
        ],
        'STL/TOV': [
            ' ', 'PLAYER', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE', 'PERIOD', 'Video Link'
        ]
    }

    columns = columns_by_type.get(df_type)
    labels_df = pd.DataFrame(columns=columns)

    return labels_df


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
        

def download_videos_from_dataframe(df: pd.DataFrame, name: str, output_dir: str, max_workers: int=8):
    """
    Descarga los vídeos de la columna 'Video Link' en paralelo y los guarda con el formato 'NAME_id'.
    
    Args:
        df (pd.DataFrame): DataFrame con los enlaces de vídeo en la columna 'Video Link'.
        name (str): Prefijo para el nombre de los archivos descargados.
        output_dir (str): Directorio donde se guardarán los vídeos.
        max_workers (int): Número máximo de hilos para la descarga en paralelo.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Filtrar las filas que tienen un enlace válido en 'Video Link'
    df = df.dropna(subset=['Video Link'])
    
    # Preparar tareas para descargar los vídeos
    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, video_url in df['Video Link'].items():
            file_name = os.path.join(output_dir, f"{name}_{idx}.mp4")
            tasks.append(executor.submit(download_video, video_url, file_name))
        
        # Mostrar barra de progreso
        for future in tqdm(tasks, desc="Descargando vídeos"):
            future.result()
