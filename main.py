import sys
import logging
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

def is_session_expired(driver):
    current_url = driver.current_url
    logging.info(f'current_url = {current_url}')

    # Check if the URL has changed to the Captcha page
    if "errorsessioninvalide" in current_url.lower():
        return True  # User is on the Captcha page, indicating session expired
    return False  # User is still on the expected page

def set_session_cookies(driver):
    jsessionid = os.getenv("JSESSIONID") or 'VM-01-48-02-003~VM-01-48-02-003l8wk3s082bsz10ab1pboc15032713851.VM-01-48-02-003'
    incap_ses_value = os.getenv("INCAP_SES") or 'TKtjcs7dYVoebWDrfSHWHmt/BmcAAAAAYiHGVmQwXDYF1to5WkNwQQ=='

    logging.info(f'jsessionid = ${jsessionid}')
    logging.info(f'incap_ses_value = ${incap_ses_value}')

    # Add JSESSIONID cookie
    driver.add_cookie({
        "name": "JSESSIONID",
        "value": jsessionid,
        "domain": "www.rdv-prefecture.interieur.gouv.fr",
        "path": "/rdvpref",
        "secure": True,
        "httpOnly": True
    })
    logging.info(f'Replaced JSESSIONID cookie with new value.')

    # Find and replace the dynamic incap_ses_* cookie
    cookies = driver.get_cookies()

    for cookie in cookies:
        if cookie['name'].startswith("incap_ses_"):
            # Replace the value of the dynamic incap_ses cookie with the one from the environment
            driver.add_cookie({
                "name": cookie['name'],
                "value": incap_ses_value,
                "domain": "www.rdv-prefecture.interieur.gouv.fr",
                "path": "/",
                "secure": False,
                "httpOnly": False
            })
            logging.info(f"Replaced {cookie['name']} cookie with new value.")

def main():
    try:
        logging.basicConfig(level=logging.INFO, format='[%(levelname)s]: %(message)s')

        if len(sys.argv) > 1:
            driver = create_chrome_driver()
        else:
            driver = create_edge_driver()
        logging.info('Driver created')

        # Set cookies BEFORE navigating to any page
        driver.get("https://www.rdv-prefecture.interieur.gouv.fr/")
        set_session_cookies(driver)
        logging.info('Cookies set')
        sleep(3)

        # Navigate to the first page
        driver.get("https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4407/cgu/")
        sleep(3)

        while True:
            logging.info(f"Execution at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            # Navigate to a page that requires Captcha cookies
            driver.get("https://www.rdv-prefecture.interieur.gouv.fr/")
            sleep(3)
            driver.get("https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4407/creneau/")
            sleep(3)

            # Check if the session has expired
            if is_session_expired(driver):
                raise Exception("Session has expired. Please update the cookies.")
            
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
            logging.info('Waiting for the next run...\n\n')
            # Wait for 10 minutes before the next execution
            sleep(60*5)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(e)
    finally:
        driver.quit()
        logging.info('Script completed')

if __name__ == "__main__":
    main()