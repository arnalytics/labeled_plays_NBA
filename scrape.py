from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import re
from tqdm import tqdm

import concurrent.futures
from selenium.webdriver.chrome.options import Options

###################################################################################################
'''
    AUXILIAR FUNCTIONS
'''
###################################################################################################

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


# Click on accept cookies
def accept_cookies(driver):
    try:
        cookie_accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]'))
        )
        cookie_accept_button.click()  # Click on 'Accept'
        print("Cookies banner closed.")
    except Exception as e:
        print("No cookies banner found or other issue:", e)


def count_rows_table(driver, table_xpath: str):
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


def find_number_of_players(driver): 
    xpath = '//*[@id="__next"]/div[2]/div[2]/div[3]/section[2]/div/div[2]/div[2]/div[1]/div[1]'

    num_of_players = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
    
    number_str = re.search(r"\d+", num_of_players.text)
    number = int(number_str.group())

    return number


def interact_w_dropdown(xpath: str, option_value: str, driver):

    try:
        dropdown_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        select = Select(dropdown_element)
        select.select_by_value(option_value)
    except:
        print("Something went wrong :(((")


def get_last_player_id(df: pd.DataFrame) -> int:
    """
    Get the player id of the last player scraped, so the scraper knows where it left it.
    """
    try:
        last_id = df['PLAYER ID'].iloc[-1]

        return int(last_id)
    except: 
        return 0
    

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
            'SEASON', 'PLAYER ID', 'PLAYER', 'PLAY TYPE', 'MADE', 'SHOT TYPE', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE',
            'PERIOD', 'TIME REMAINING', 'SHOT DISTANCE (FT)', 'TEAM', 'AST', 'Assisted by', 'Video Link'
        ],
        'OREB': [
            'SEASON', 'PLAYER ID', 'PLAYER NAME', 'REBOUND TYPE', 'PLAY DESCRIPTION', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE', 'PERIOD', 'Video Link'
        ],
        'DREB': [
            'SEASON', 'PLAYER ID', 'PLAYER NAME', 'REBOUND TYPE', 'PLAY DESCRIPTION', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE', 'PERIOD', 'Video Link'
        ],
        'BLK': [
            'SEASON', 'PLAYER ID', 'PLAYER', 'PLAY DESCRIPTION', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE', 'PERIOD', 'Video Link'
        ],
        'STL/TOV': [
            'SEASON', 'PLAYER ID', 'PLAYER', 'BOXSCORE', 'VTM', 'HTM', 'GAME DATE', 'PERIOD', 'Video Link'
        ]
    }

    columns = columns_by_type.get(df_type)
    labels_df = pd.DataFrame(columns=columns)

    return labels_df


def initialize_df(play_type: str, season: str):
    df_path = f'/Users/arnaubarrera/Desktop/MSc Computer Vision/TFM/labeled_plays_NBA/holy_grail/labels/{play_type}_{season}_labels.csv'
    
    try: # If the dataframe already exists, read it
        labels_df = pd.read_csv(df_path)

    except:  # If the dataframe doesn't exist, create an empty one w/ the headers
        labels_df = create_dataframe(play_type)
        labels_df.to_csv(df_path, mode='w', index=False, header=True)

    return labels_df, df_path


###################################################################################################
'''
    SCRAPING FUNCTIONS
'''
###################################################################################################

def scrape_rebounds(season: str, play_type: str):
    """
    Scrapes basketball player data for a specified season and play type from a web page.

    This function initializes a Selenium WebDriver, navigates to the specified web page,
    and collects data related to basketball plays for each player in the given season. 
    The collected data is saved into a CSV file.

    Parameters:
    -----------
    season : str
        The season for which to scrape data, formatted as 'YYYY-YY'. 
        For example, '2021-22'.

    play_type : str
        The type of play to scrape data for. This should be one of the following:
        - 'OREB' for offensive rebounds
        - 'DREB' for defensive rebounds

    Returns:
    --------
    None
        This function does not return any value. Instead, it writes the scraped data
        to a CSV file specified within the function.

    """

    driver = initialize_driver(season)
    
    # Definir xpath general y otras variables
    general_players_table_xpath = '//*[@id="__next"]/div[2]/div[2]/div[3]/section[2]/div/div[2]/div[3]/table/'
    play_type_indices = {"FGA": 11, "OREB": 19, "DREB": 20, "REB": 21, "TOV": 23, "STL": 24, "BLK": 25}
    
    # Inicializar DataFrame y path del csv (considera que cada proceso escriba a un archivo distinto)
    labels_df, df_path = initialize_df(play_type, season)
    number = find_number_of_players(driver)
    
    last_id = get_last_player_id(labels_df)

    for i in tqdm(range(last_id + 1, number + 1), desc=f"{season} - Procesando jugadores"):
        # Resetear el dataframe para cada jugador
        labels_df = labels_df.iloc[0:0]
        
        # Cargar todos los jugadores en la página
        interact_w_dropdown(
            '//*[@id="__next"]/div[2]/div[2]/div[3]/section[2]/div/div[2]/div[2]/div[1]/div[3]/div/label/div/select',
            '-1',
            driver
        )

        # Nombre del jugador
        xpath_player_name = f'//*[@id="__next"]/div[2]/div[2]/div[3]/section[2]/div/div[2]/div[3]/table/tbody/tr[{i}]/td[2]/a'
        player_name = driver.find_element(By.XPATH, xpath_player_name).text
        player_id = i
    
        # Clicar en la columna correspondiente al tipo de jugada
        link_xpath = general_players_table_xpath + f'tbody/tr[{i}]/td[{play_type_indices[play_type]}]/a'
        link_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, link_xpath))
        )
        link_url = link_element.get_attribute("href")
        driver.get(link_url)
    
        video_display_xpath = '//*[@id="vjs_video_3_html5_api"]'
    
        # Seleccionar 'All' en el dropdown para cargar todas las filas
        interact_w_dropdown(
            '//*[@class="DropDown_select__4pIg9"]', 
            '-1', 
            driver
        )
    
        rows_number = count_rows_table(driver, table_xpath='//*[@id="__next"]/div[2]/div[2]/div[3]/section/div/div/div[3]/table/tbody')
    
        for j in range(1, rows_number+1): 
            line_play = f'//*[@id="__next"]/div[2]/div[2]/div[3]/section/div/div/div[3]/table/tbody/tr[{j}]/td'
    
            play = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, line_play))
            )
    
            columns_play = play.find_elements(By.XPATH, line_play)
            
            row_data = [col.text for col in columns_play]
            row_data[0] = season
            row_data.insert(1, player_id)
            row_data.insert(2, player_name)
            row_data.insert(3, play_type)
    
            play.click()
    
            # Obtener el video
            video_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, video_display_xpath))
            )
            video_src = video_element.get_attribute('src')
            row_data.append(video_src)
    
            # Agregar la fila al DataFrame
            labels_df = pd.concat([labels_df, pd.DataFrame([row_data], columns=labels_df.columns)], ignore_index=True)  
        
        # Guardar en CSV (podrías incluir la temporada en el nombre del archivo para diferenciarlos)
        labels_df.to_csv(df_path, mode='a', index=False, header=False)
    
        # Volver atrás para el siguiente jugador
        driver.back()
        time.sleep(2)
    
    driver.quit()


def scrape_shots(season: str, play_type: str):
    # TODO

    season = -1
    play_type = -1

    return season + play_type


###################################################################################################
'''
    MAIN
'''
###################################################################################################


if __name__ == '__main__':
    
    # Lista de temporadas
    all_seasons = ["2014-15", "2015-16", "2016-17", "2017-18", "2018-19", 
                   "2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]

    # Lista de tipos de jugadas
    play_types = ["DREB", "OREB"]

    for play_type in play_types:  # Ejecuta dos loops, uno para cada tipo de jugada
        print(f"Iniciando scraping para {play_type}...\n")
        
        for season in all_seasons:
            try:
                print(f"Iniciando scraping para {play_type} en la temporada {season}...")
                scrape_rebounds(season, play_type)
                print(f"craping completado para {play_type} en {season}.\n")
            except Exception as e:
                print(f"Error en {play_type}, temporada {season}: {e}. Pasando a la siguiente...\n")

        print(f"Scraping finalizado para {play_type}.\n")

    print("Proceso finalizado para todos los tipos de jugadas y temporadas.")

