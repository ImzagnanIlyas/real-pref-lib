import google.generativeai as genai
import os
import sys
import logging
import base64
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from time import sleep
import os
import chromedriver_autoinstaller
from datetime import datetime

def create_edge_driver():
    options = webdriver.EdgeOptions()
    options.add_argument("--log-level=3")  # Suppress most logs
    options.add_experimental_option("excludeSwitches", ["enable-logging"])  # Disable DevTools logging
    
    # Create a Service object with the path to msedgedriver.exe
    webservice = EdgeService(executable_path='C:/src/edgedriver/msedgedriver.exe')
    
    # Initialize the Edge WebDriver with the user profile
    driver = webdriver.Edge(service=webservice, options=options)
    
    return driver

def create_chrome_driver():
    # Automatically install the ChromeDriver that matches the current Chrome version
    webdriver_path = chromedriver_autoinstaller.install()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run browser in headless mode
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")  # Suppress most logs
    options.add_experimental_option("excludeSwitches", ["enable-logging"])  # Disable DevTools logging
    
    # Create a Service object with the path to msedgedriver.exe
    webservice = ChromeService(executable_path=webdriver_path)
    
    # Initialize the Edge WebDriver with the user profile
    return webdriver.Chrome(service=webservice, options=options)


def main():
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s]: %(message)s')

    if len(sys.argv) > 1:
        driver = create_chrome_driver()
    else:
        driver = create_edge_driver()
    logging.info('Driver created')

    model = genai.GenerativeModel("gemini-1.5-flash")

    # Navigate to the first page
    driver.get("https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4407/cgu/")
    sleep(5)

    captcha_not_resolved = True
    max_attempts = 7  # Set the maximum number of attempts
    attempt_count = 0  # Initialize attempt counter

    while captcha_not_resolved and attempt_count < max_attempts:
        try:
            attempt_count += 1
            logging.info("Resolving Captcha...")
            # Locate the captcha image element by its ID
            captcha_img = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, 'captchaFR_CaptchaImage'))
            )
            # Use JavaScript to convert the blob image to a base64 string
            image_data = driver.execute_script("""
                var img = arguments[0];
                var canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                var ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                return canvas.toDataURL('image/png').substring(22);  // Remove the 'data:image/png;base64,' part
            """, captcha_img)

            # Decode the base64 string to binary image data
            image_bytes = base64.b64decode(image_data)

            # Save the image as a PNG file
            with open("captcha_image.png", "wb") as f:
                f.write(image_bytes)
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

            
            myfile = genai.upload_file("captcha_image.png")
            result = model.generate_content(
                [myfile, "\n\n", "Give me an answer only with the text in this captcha? Hint: captcha has only alphabets and digits"]
            )
            try:
                captcha_value = result.text.replace(" ", "").replace("\n", "")
                logging.info(f"{captcha_value=}")
            except:
                logging.error("Model Error")
                driver.get("https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4407/cgu/")
                sleep(5)
                continue
            
            captcha_input = driver.find_element(By.ID, "captchaFormulaireExtInput")
            driver.execute_script("arguments[0].scrollIntoView(true);", captcha_input)
            captcha_input.clear()
            captcha_input.send_keys(captcha_value)

            submit_button = driver.find_element(By.XPATH, "//*[@id='contenu']/section/div/div/form/div[2]/button")
            submit_button.click()
            sleep(5)

            current_url = driver.current_url
            if "creneau" in current_url.lower():
                captcha_not_resolved = False
            else:
                logging.warning("Resolving Captcha Faild")
        except Exception as e:
            logging.error(e)
    
    # If captcha not resolved, exit the program gracefully
    if captcha_not_resolved:
        logging.error(f"Maximum attempts ({max_attempts}) reached. Ending program.")
        driver.quit()
        sys.exit(0)

    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[text() = "Aucun créneau disponible"]'))
        )
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[text() = "Veuillez réessayer ultérieurement."]'))
        )
    except TimeoutException:
        raise Exception("Change detected. Check the appointments page")
    
    logging.info('No changes detected. Appointment not found')
    driver.quit()
    logging.info('Script completed')
    

if __name__ == "__main__":
    main()