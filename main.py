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
