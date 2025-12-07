from mcod.tags.forms import TagForm


def test_form_doesnt_validate_if_tag_exists(tag, tag_pl):
    data = {
        "name": tag_pl.name,
        "language": tag_pl.language,
    }
    form = TagForm(data=data)
    assert not form.is_valid()


def test_form_validates_tag_is_valid():
    data = {
        "name": "TEST12",
        "language": "pl",
    }
    form = TagForm(data=data)
    assert form.is_valid()


def test_form_validates_if_tag_exists_in_other_language(tag_pl, tag_en):
    data = {
        "name": tag_pl.name,
        "language": tag_en.language,
    }
    form = TagForm(data=data)
    assert form.is_valid()
