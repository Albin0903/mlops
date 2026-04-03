import sys

from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TusmoBot:
    def __init__(self, headless: bool = False):
        # Pour une execution CI/CD sans vue, headless serait True.
        self.driver = Chrome()
        self.driver.set_window_size(0, 400)
        self.base_url = "https://www.tusmo.xyz"

    def connect(self, room_url: str) -> tuple[str, int]:
        self.driver.get(self.base_url)
        wait = WebDriverWait(self.driver, 10)

        # Passage en francais
        selecteur = "#app > div > div.menu > div.w-full.h-14.mt-6.flex.justify-between.relative > div > button > img"
        langue_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selecteur)))
        langue_element.click()

        selecteur_fr = "#app > div > div.menu > div.w-full.h-14.mt-6.flex.justify-between.relative > div.langs-container.button-group > button:nth-child(1)"
        bouton_francais = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selecteur_fr)))
        bouton_francais.click()

        if room_url:
            self.driver.get(f"{self.base_url}/{room_url}")

        # Attente de la grille pour lire la lettre de depart et la longueur
        grid_selector = "#app > div > div.game-wrapper > div.game-center > div > div > div.flex.flex-col.grow.items-center.justify-end.pb-2.w-full > div.motus-grid"
        grid_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, grid_selector)))

        lignes = grid_element.text.split("\n")
        first_letter = grid_element.text.split()[0][0]
        # La longueur reelle du mot correspond souvent au nombre de colonnes de la premiere ligne
        word_length = len(lignes[0]) if len(lignes) > 0 else 6

        return first_letter, word_length

    def lire_reponse(self, longueur: int, nb_essais: int) -> str:
        self.driver.refresh()
        wait = WebDriverWait(self.driver, 10)
        grid_selector = "#app > div > div.game-wrapper > div.game-center > div > div > div.flex.flex-col.grow.items-center.justify-end.pb-2.w-full > div.motus-grid"
        grid_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, grid_selector)))

        raw_words = grid_element.text.split()
        if len(raw_words) <= nb_essais * longueur:
            return ""

        mot = "".join(raw_words[nb_essais * longueur : longueur * (nb_essais + 1)])
        mot = mot[0].upper() + mot[1:].lower()
        res = ""

        cell_contents = grid_element.find_elements(By.CLASS_NAME, "cell-content")
        for i in range(longueur):
            idx = i + (nb_essais * longueur)
            if idx >= len(cell_contents):
                res += "_"
                continue

            bg_color = cell_contents[idx].value_of_css_property("background-color")
            if bg_color == "rgba(219, 58, 52, 1)":
                res += mot[i].upper()
            elif bg_color == "rgba(247, 183, 53, 1)":
                res += mot[i].lower()
            else:
                res += "_"
        return res

    def close(self):
        try:
            self.driver.quit()
        except BaseException as e:
            print(f"info: Error closing driver: {e}", file=sys.stderr)
