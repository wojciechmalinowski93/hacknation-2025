import pytest
from bs4 import BeautifulSoup

from mcod.lib.widgets import OpennessScoreStars


@pytest.mark.parametrize("openness_score", (1, 2, 3, 4, 5))
def test_openness_score_widget(openness_score: int) -> None:
    rendered = OpennessScoreStars().render(name="openness_score", value=openness_score)
    soup = BeautifulSoup(rendered, "html.parser")
    found_stars = 0
    for element in soup.find_all("span"):
        found_stars += int("★" == element.text)
    assert found_stars == openness_score


def test_openness_score_widget_for_zero_stars() -> None:
    max_openness_score = 5
    rendered = OpennessScoreStars().render(name="openness_score", value=0)
    soup = BeautifulSoup(rendered, "html.parser")
    found_stars = 0
    found_text_comment = False
    for element in soup.find_all("span"):
        found_stars += int("★" == element.text)
        found_text_comment = f" (0 / {max_openness_score})" == element.text
    assert found_stars == 0
    assert found_text_comment


def test_openness_score_widget_for_out_of_bands() -> None:
    max_openness_score = 5
    rendered = OpennessScoreStars().render(name="openness_score", value=6)
    soup = BeautifulSoup(rendered, "html.parser")
    found_stars = 0
    for element in soup.find_all("span"):
        found_stars += int("★" == element.text)
    assert found_stars == max_openness_score


@pytest.mark.parametrize(
    "value, normalised_value, max_openness_score",
    (
        (-10, 0, 5),
        (0, 0, 5),
        (1, 1, 5),
        (2, 2, 5),
        (3, 3, 5),
        (4, 4, 5),
        (5, 5, 5),
        (6, 5, 5),
        (6, 6, 6),
    ),
)
def test_score_as_list(value: int, normalised_value: int, max_openness_score: int) -> None:
    actual = OpennessScoreStars._score_as_list(value, max_openness_score)
    assert len(actual) == max_openness_score
    assert actual.count(True) == normalised_value
    for idx, is_filled in enumerate(actual):
        if idx < value:
            assert is_filled
        else:
            assert not is_filled
