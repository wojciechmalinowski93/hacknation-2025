import json

from mcod.lib.widgets import JsonPairDatasetInputs


class TestJsonPairDatasetInputs:
    def test_render_without_value(self):
        widget = JsonPairDatasetInputs()
        expected = (
            '<input type="text" name="json_key[customfields]" value="key">'
            '<input type="text" name="json_value[customfields]" value="value" class="customfields"><br>'
        )
        actual = widget.render("customfields", "{}")
        assert expected == actual

    def test_render_with_value(self):
        widget = JsonPairDatasetInputs()
        data = json.dumps({"james": "bond"})

        expected = (
            '<input type="text" name="json_key[customfields]" value="james">'
            '<input type="text" name="json_value[customfields]" value="bond" class="customfields"><br>'
        )
        actual = widget.render("customfields", data)
        assert expected == actual
