from collections import Counter

from scripts.tusmo.dictionary import TusmoDictionary


class TusmoSolver:
    def __init__(self, longueur: int, lettre_depart: str, db: TusmoDictionary = None):
        self.longueur = longueur
        self.lettre_depart = lettre_depart.lower() if lettre_depart else ""
        self.db = db if db else TusmoDictionary()

        self.candidats = self.db.get_words(longueur, self.lettre_depart)
        self.vocabulaire_test = self.candidats.copy()

        self.lettres_absentes = set()
        self.lettres_bien_placees = [""] * longueur
        if self.lettre_depart:
            self.lettres_bien_placees[0] = self.lettre_depart

        self.lettres_mal_placees = [set() for _ in range(longueur)]
        self.compteur_min_lettres = Counter()
        self.compteur_max_lettres = {}

    def mettre_a_jour_contraintes(self, mot_joue: str, motif_reponse: str) -> None:
        compteur_local = Counter()
        mot_joue = mot_joue.lower()

        for i, (lettre, code) in enumerate(zip(mot_joue, motif_reponse, strict=False)):
            if code.isupper():
                self.lettres_bien_placees[i] = lettre
                compteur_local[lettre] += 1
            elif code.islower():
                self.lettres_mal_placees[i].add(lettre)
                compteur_local[lettre] += 1

        for _, (lettre, code) in enumerate(zip(mot_joue, motif_reponse, strict=False)):
            if code == "_" or code == " ":
                if compteur_local[lettre] > 0:
                    self.compteur_max_lettres[lettre] = compteur_local[lettre]
                else:
                    self.lettres_absentes.add(lettre)

        for lettre, count in compteur_local.items():
            if count > self.compteur_min_lettres[lettre]:
                self.compteur_min_lettres[lettre] = count

    def est_valide(self, mot: str) -> bool:
        for i, lettre_ref in enumerate(self.lettres_bien_placees):
            if lettre_ref and mot[i] != lettre_ref:
                return False

        for i, interdit_set in enumerate(self.lettres_mal_placees):
            if mot[i] in interdit_set:
                return False

        for lettre in self.lettres_absentes:
            if lettre in mot:
                return False

        compte_mot = Counter(mot)
        for lettre, min_count in self.compteur_min_lettres.items():
            if compte_mot[lettre] < min_count:
                return False

        for lettre, max_count in self.compteur_max_lettres.items():
            if compte_mot[lettre] > max_count:
                return False

        return True

    def filtrer_candidats(self) -> int:
        self.candidats = [mot for mot in self.candidats if self.est_valide(mot)]
        return len(self.candidats)

    def obtenir_meilleur_mot(self) -> str | None:
        nb_candidats = len(self.candidats)
        if nb_candidats == 0:
            return None
        if nb_candidats == 1:
            return self.candidats[0]

        occurences = Counter()
        for mot in self.candidats:
            for lettre in set(mot):
                occurences[lettre] += 1

        def score_entropie(mot: str) -> float:
            score = 0
            for lettre in set(mot):
                count = occurences.get(lettre, 0)
                p = count / nb_candidats
                information = p * (1 - p)
                score += information

            if mot in self.candidats:
                score += 0.15
            return score

        population = self.candidats if nb_candidats > 1000 else self.vocabulaire_test
        meilleur_mot = max(population, key=score_entropie)
        return meilleur_mot
