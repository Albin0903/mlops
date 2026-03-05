"""
tests/test_schemas.py — tests de validation des schemas pydantic.
verifie que les entrees invalides sont rejetees et les valeurs par defaut correctes.
"""

import pytest
from pydantic import ValidationError
from app.schemas.analysis import AnalysisRequest


class TestAnalysisRequestDefaults:
    """tests sur les valeurs par defaut du schema"""

    def test_minimal_valid_request(self):
        """une requete avec seulement 'content' doit etre valide"""
        req = AnalysisRequest(content="print('hello')")
        assert req.content == "print('hello')"
        assert req.language == "python"
        assert req.mode == "doc"
        assert req.question is None

    def test_default_language_is_python(self):
        """le langage par defaut doit etre python"""
        req = AnalysisRequest(content="code")
        assert req.language == "python"

    def test_default_mode_is_doc(self):
        """le mode par defaut doit etre doc"""
        req = AnalysisRequest(content="code")
        assert req.mode == "doc"


class TestAnalysisRequestValidation:
    """tests de validation stricte des entrees"""

    def test_empty_content_rejected(self):
        """un contenu vide doit lever une erreur de validation"""
        with pytest.raises(ValidationError):
            AnalysisRequest(content="")

    def test_missing_content_rejected(self):
        """le champ content est obligatoire"""
        with pytest.raises(ValidationError):
            AnalysisRequest()

    def test_invalid_mode_rejected(self):
        """un mode autre que 'doc' ou 'question' doit etre rejete"""
        with pytest.raises(ValidationError):
            AnalysisRequest(content="code", mode="invalid")

    def test_mode_doc_accepted(self):
        """le mode 'doc' est valide"""
        req = AnalysisRequest(content="code", mode="doc")
        assert req.mode == "doc"

    def test_mode_question_accepted(self):
        """le mode 'question' est valide"""
        req = AnalysisRequest(content="texte", mode="question", question="quoi ?")
        assert req.mode == "question"


class TestAnalysisRequestQuestionMode:
    """tests specifiques au mode question"""

    def test_question_field_optional_in_doc_mode(self):
        """la question est optionnelle en mode doc"""
        req = AnalysisRequest(content="code", mode="doc")
        assert req.question is None

    def test_question_field_accepted_in_question_mode(self):
        """la question est acceptee en mode question"""
        req = AnalysisRequest(
            content="document technique",
            mode="question",
            question="quel framework est utilise ?"
        )
        assert req.question == "quel framework est utilise ?"

    def test_custom_language(self):
        """un langage personnalise doit etre accepte"""
        req = AnalysisRequest(content="code", language="rust")
        assert req.language == "rust"
