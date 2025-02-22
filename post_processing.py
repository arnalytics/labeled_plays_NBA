import pandas as pd
import unicodedata
import os
from typing import Union, List


def read_csv(play_type: str, season: str, player_name: str = None, player_id: int = None) -> pd.DataFrame:
    """
    Lee un archivo CSV y filtra las filas según player_name y/o player_id.
    
    Args:
        play_type (str): Tipo de jugada (ej. 'OREB' o 'DREB').
        season (str): Temporada (ej. '2015-16').
        player_name (str, optional): Nombre del jugador a filtrar.
        player_id (int, optional): ID del jugador a filtrar.

    Returns:
        pd.DataFrame: DataFrame con los datos filtrados (o sin filtrar si no se especifican condiciones).
    """

    # Auxiliar function
    def normalize_string(s: str) -> str:
        """
        Normaliza una cadena eliminando acentos y convirtiéndola a minúsculas.
        """
        return ''.join(
            c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn'
        )

    # Construir el nombre del archivo
    file_path = f'holy_grail/labels/{play_type}_{season}_labels.csv'

    try:
        # Leer el archivo CSV
        df = pd.read_csv(file_path)

        # Si no se especifican filtros, devolver el DataFrame completo
        if player_name is None and player_id is None:
            return df

        # Aplicar filtros según los parámetros dados
        if player_name is not None:
            normalized_player_name = normalize_string(player_name)
            df = df[df['PLAYER NAME'].apply(lambda x: normalize_string(str(x)) == normalized_player_name)]

        if player_id is not None:
            df = df[df['PLAYER ID'] == player_id]

        return df

    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no existe.")
        return pd.DataFrame()  # Retorna un DataFrame vacío si el archivo no se encuentra
    except Exception as e:
        print(f"Error al leer el archivo {file_path}: {e}")
        return pd.DataFrame()  # Retorna un DataFrame vacío en caso de error inesperado


def concatenate_playtype_seasons(play_type: str, seasons: Union[str, List[str]], save: bool = False) -> pd.DataFrame:
    """
    Concatena los archivos CSV de un tipo de jugada y una lista de temporadas en un solo DataFrame,
    ordenados por temporada de manera creciente.
    Opcionalmente, guarda el DataFrame concatenado en un archivo CSV.

    Args:
        play_type (str): Tipo de jugada (ej. 'OREB' o 'DREB').
        seasons (Union[str, List[str]]): Lista de temporadas (ej. ['2022-23', '2022-24']) o 'All' para incluir todas.
        save (bool): Si es True, guarda el DataFrame en un archivo CSV.

    Returns:
        pd.DataFrame: DataFrame concatenado con los datos de todas las temporadas seleccionadas.
    """
    
    # Verify inputs
    valid_seasons = ["2014-15", "2015-16", "2016-17", "2017-18", "2018-19", 
                     "2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
    
    if isinstance(seasons, str) and seasons.lower() == 'all':
        seasons = 'All'
    
    if seasons != "All":
        # Si seasons es una lista, verificar cada uno; si es un string, verificarlo directamente
        if isinstance(seasons, list):
            if not all(season in valid_seasons for season in seasons):
                raise ValueError("Algunas temporadas no son válidas. Las temporadas válidas son: " + ", ".join(valid_seasons))
        elif seasons not in valid_seasons:
            raise ValueError("La temporada no es válida. Las temporadas válidas son: " + ", ".join(valid_seasons))

    # Get files in th folder
    folder_path = "holy_grail/labels/"

    all_files = os.listdir(folder_path)
    
    # Filtrar archivos que coincidan con el formato esperado
    csv_files = [f for f in all_files if f.startswith(f"{play_type}_") and f.endswith("_labels.csv")]

    # Si seasons es 'All', seleccionar todas las temporadas disponibles en orden creciente
    if seasons == "All":
        season_order = sorted(set(f.split("_")[1] for f in csv_files))  # Extraer temporadas y ordenarlas
    else:
        season_order = sorted(seasons)  # Ordenar las temporadas dadas

    # Filtrar los archivos según el orden de las temporadas
    selected_files = [f for season in season_order for f in csv_files if season in f]

    dataframes = []
    
    for file in selected_files:
        file_path = os.path.join(folder_path, file)
        try:
            df = pd.read_csv(file_path)
            dataframes.append(df)
        except Exception as e:
            print(f"Error al leer {file}: {e}")

    # Concatenar todos los DataFrames encontrados
    if dataframes:
        final_df = pd.concat(dataframes, ignore_index=True)

        # Guardar el DataFrame si save=True
        if save:
            output_filename = f"{play_type}_all.csv" if seasons == "All" else f"{play_type}_{'_'.join(season_order)}_concat.csv"
            output_path = os.path.join(folder_path, output_filename)
            final_df.to_csv(output_path, index=False)
            print(f"Archivo guardado en: {output_path}")

        return final_df
    else:
        print("No se encontraron archivos para las temporadas indicadas.")
        return pd.DataFrame()  # Retorna un DataFrame vacío si no hay archivos


def clean_missing_video_data(filename: str, overwrite: bool = False) -> None:
    """
    Lee un archivo CSV, elimina las filas con el video faltante o valores vacíos en la columna 'Video Link',
    y guarda el resultado en la misma carpeta, ya sea sobrescribiendo el archivo original o creando uno nuevo.

    :param filename: Nombre del archivo CSV (sin ruta).
    :param overwrite: Si es True, sobrescribe el archivo original. Si es False, guarda el resultado con "_cleaned" agregado al nombre.
    """
    try:
        # Definir el path donde se encuentran los archivos
        base_path = "holy_grail/labels/"  # Cambia esto según la ubicación real de tus archivos
        file_path = os.path.join(base_path, filename)

        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo {file_path} no existe.")

        # Leer el archivo CSV
        df = pd.read_csv(file_path)

        # Verificar si la columna 'Video Link' existe en el DataFrame
        if 'Video Link' not in df.columns:
            raise ValueError("El archivo CSV no contiene la columna 'Video Link'.")

        # Filtrar las filas donde 'Video Link' no sea el video faltante, vacío o NaN
        df_cleaned = df[(df['Video Link'] != 'https://videos.nba.com/nba/static/missing.mp4') & 
                        df['Video Link'].notna() & 
                        (df['Video Link'] != '')]

        # Determinar la ruta de salida según overwrite
        if overwrite:
            output_file = file_path  # Sobrescribe el archivo original
        else:
            output_file = os.path.join(base_path, filename.replace(".csv", "_cleaned.csv"))  # Crea un nuevo archivo

        # Guardar el archivo limpio
        df_cleaned.to_csv(output_file, index=False)
        print(f"Archivo limpio guardado en: {output_file}")

    except Exception as e:
        print(f"Error al procesar el archivo: {e}")

