import datetime
import io
import json
import tempfile
from pathlib import Path
from xml.dom.minidom import parseString

import pandas as pd
import pytest
from django.test import override_settings
from pyexpat import ExpatError
from pytest_mock import MockerFixture

from mcod.core.utils import (
    CSVWriter,
    FileMeta,
    XmlTextInvalid,
    XMLWriter,
    clean_columns_in_dataframe,
    get_file_metadata,
    prepare_error_folder,
    save_df_to_xlsx,
)


class TestCleanColumnsInDataframe:
    def test_clean_single_column(self):
        df = pd.DataFrame({"ColumnName1": [" Value1 ", "Value2", None, "Value3 "], "ColumnName2": [0, 10, 20, 30]})

        cleaned_df: pd.DataFrame = clean_columns_in_dataframe(df, "ColumnName1").reset_index(drop=True)
        expected_df = pd.DataFrame({"ColumnName1": [" Value1 ", "Value2", "Value3 "], "ColumnName2": [0, 10, 30]})
        pd.testing.assert_frame_equal(cleaned_df, expected_df)

    def test_clean_multiple_columns(self):
        df = pd.DataFrame(
            {"ColumnName1": [" Value1 ", "Value2", None, "Value3 "], "ColumnName2": [" Value4", "   ", "", "Value5"]}
        )

        cleaned_df: pd.DataFrame = clean_columns_in_dataframe(df, "ColumnName1", "ColumnName2").reset_index(drop=True)
        expected_df = pd.DataFrame({"ColumnName1": [" Value1 ", "Value3 "], "ColumnName2": [" Value4", "Value5"]})
        pd.testing.assert_frame_equal(cleaned_df, expected_df)

    def test_non_existent_column(self):
        df = pd.DataFrame({"ColumnName1": ["Value1", "Value2", "Value3"], "ColumnName2": [10, 20, 30]})
        cleaned_df: pd.DataFrame = clean_columns_in_dataframe(df, "NonExistentColumn")
        pd.testing.assert_frame_equal(df, cleaned_df)


def test_save_df_to_xlsx_smoke():
    data = {"Column1": [1, 2, 3], "Column2": ["4", "5", "6"], "Column3": [7, "8 ", None]}
    df = pd.DataFrame(data)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = Path(temp_dir, "file_name.xlsx")
        # Given
        assert not temp_file_path.exists()
        # When
        save_df_to_xlsx(df, temp_file_path)
        # Then
        assert temp_file_path.exists()


def test_get_file_metadata_with_existing_file_returns_expected_size_and_tzinfo(tmp_path):
    file = tmp_path / "sample.txt"
    content = "hello world"
    file.write_text(content)
    meta = get_file_metadata(file)

    assert isinstance(meta, FileMeta)
    assert meta.size == len(content)
    assert isinstance(meta.created, datetime.datetime)
    assert isinstance(meta.modified, datetime.datetime)
    assert isinstance(meta.accessed, datetime.datetime)
    assert meta.created.tzinfo == datetime.timezone.utc
    assert meta.modified.tzinfo == datetime.timezone.utc
    assert meta.accessed.tzinfo == datetime.timezone.utc


def test_get_file_metadata_respects_custom_timezone(tmp_path):
    file = tmp_path / "sample.txt"
    file.write_text("abc")
    tz = datetime.timezone(datetime.timedelta(hours=2))
    meta = get_file_metadata(file, tz_info=tz)

    assert meta.created.tzinfo == tz
    assert meta.modified.tzinfo == tz
    assert meta.accessed.tzinfo == tz


def test_get_file_metadata_empty_file_has_zero_size(tmp_path):
    file = tmp_path / "empty.txt"
    file.touch()
    meta = get_file_metadata(file)

    assert meta.size == 0


def test_get_file_metadata_raises_for_missing_file(tmp_path):
    file = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        get_file_metadata(file)


def test_csv_writer():
    """
    Test CSVWriter class save() method.
    Class should write data to given file.
    """
    data = [{"some header": "some value"}]
    writer = CSVWriter(headers=list(data[0].keys()))
    xml_file = io.StringIO()
    writer.save(data=data, file_object=xml_file)
    output = xml_file.getvalue()

    assert "some value" in output


def test_xml_writer(mocker: "MockerFixture"):
    """
    Validates 'XMLWriter' save functionality.

    Simulates a save operation using predefined data to verify that the generated XML
    content matches the expected XML structure defined in 'expected_output'.
    Performs a direct comparison of the generated XML output against the XML structure
    created with 'parseString' and 'toprettyxml'.

    Args:
    - mocker (MockerFixture): Pytest mocker fixture for mocking objects.
    """

    def new_callable(parent):
        data = {"new_tag": "tag"}
        return data.get(parent, "item")

    mocker.patch.object(XMLWriter, "custom_item_func", wraps=new_callable)

    data = {"new_tag": ["some_data", "some_data2"]}
    xml_file = io.StringIO()
    writer = XMLWriter()
    writer.save(file_object=xml_file, data=data)
    output = xml_file.getvalue()

    expected_output = (
        b'<?xml version="1.0" encoding="UTF-8" ?>'
        b"<catalog>"
        b"<new_tag>"
        b"<tag>some_data</tag>"
        b"<tag>some_data2</tag>"
        b"</new_tag>"
        b"</catalog>"
    )

    assert output == parseString(expected_output).toprettyxml()


_XML_EXC = (ExpatError, XmlTextInvalid, UnicodeEncodeError)


@pytest.mark.parametrize(
    "char, expected_serialized, expect_error",
    [
        # ---- ALLOWED (should pass) ----
        ("&", "&amp;", None),
        ("<", "&lt;", None),
        (">", "&gt;", None),
        ('"', '"', None),
        ("'", "'", None),
        ("-", "-", None),
        ("*", "*", None),
        ("\u00A0", "\u00A0", None),  # non-breaking space
        ("\u200B", "\u200B", None),  # zero-width space
        ("😀", "😀", None),  # emoji
        ("\x85", "\x85", None),  # NEL (C1) — allowed in non-STRICT
        ("\U0010FFFF", "\U0010FFFF", None),  # highest valid code point — OK
        ("&#x26;", "&amp;#x26;", None),  # numeric entity treated literally (no unescape)
        ("&#x02;", "&amp;#x02;", None),  # numeric entity treated literally (no unescape)
        # ---- DISALLOWED (should raise) ----
        ("\x02", None, _XML_EXC),  # Start of Text (control char)
        ("\x00", None, _XML_EXC),  # NULL
        ("\x0B", None, _XML_EXC),  # Vertical Tab
        ("\x0C", None, _XML_EXC),  # Form Feed
    ],
)
def test_xml_writer_characters(mocker: MockerFixture, char, expected_serialized, expect_error):
    def new_callable(parent):
        data = {"new_tag": "tag"}
        return data.get(parent, "item")

    mocker.patch.object(XMLWriter, "custom_item_func", wraps=new_callable)

    data = {"new_tag": ["some_data", f"some_data2{char}"]}
    xml_file = io.StringIO()
    writer = XMLWriter()

    if expect_error:
        with pytest.raises(expect_error):
            writer.save(file_object=xml_file, data=data)
        return

    writer.save(file_object=xml_file, data=data)
    output = xml_file.getvalue()

    expected_xml = (
        f'<?xml version="1.0" encoding="UTF-8" ?>'
        f"<catalog>"
        f"<new_tag>"
        f"<tag>some_data</tag>"
        f"<tag>some_data2{expected_serialized}</tag>"
        f"</new_tag>"
        f"</catalog>"
    ).encode("utf-8")

    assert output == parseString(expected_xml).toprettyxml()


def test_xml_writer_raise_exception(mocker: "MockerFixture", tmp_path: Path):
    """
    Validates 'XMLWriter' handling of illegal characters.

    Verifies that the 'XMLWriter' raises an 'ExpatError' when illegal characters
    are present in the data. Additionally, checks for the creation of a JSON file
    containing the data intended to be saved.

    Test Scenario:
    - Patches 'custom_item_func' to manage XML writing.
    - Sets up a temporary error folder using 'prepare_error_folder'.
    - Defines data with an illegal character ('\x02') in 'new_tag'.
    - Attempts data saving using 'XMLWriter', expecting an 'ExpatError'.
    - Verifies the creation of a JSON file with the intended data.

    Args:
    - mocker (MockerFixture): Pytest mocker fixture for object mocking.
    - tmp_path (path-like): Temporary directory provided by pytest for testing.
    """

    def new_callable(parent: str) -> str:
        xml_tags = {"new_tag": "tag"}
        return xml_tags.get(parent, "item")

    mocker.patch.object(XMLWriter, "custom_item_func", wraps=new_callable)
    mocker.patch("mcod.core.utils.prepare_error_folder", return_value=tmp_path)

    data = {"new_tag": ["some_data", "something\x02to_test"]}
    xml_file = io.StringIO()
    writer: XMLWriter = XMLWriter()
    with pytest.raises(ExpatError), override_settings(METADATA_MEDIA_ROOT=tmp_path):
        writer.save(file_object=xml_file, data=data, language_catalog_path=str(tmp_path))

    expected_error_file_path = f"{tmp_path}/data.json"
    assert Path(expected_error_file_path).is_file()

    with open(expected_error_file_path, "r") as file:
        file_data = json.loads(file.read())
        assert file_data == data


def test_prepare_error_folder(tmp_path: Path):
    """
    Test to ensure 'prepare_error_folder' function operates as expected.

    It verifies the functionality of 'prepare_error_folder' by:
    - Creating a new folder 'parsing_errors' inside the temporary path.
    - Creating a file 'new_file.txt' inside the 'parsing_errors' folder.
    - Checking if 'prepare_error_folder' correctly manipulates the folder.

    The test validates that after invoking 'prepare_error_folder':
    - The old file 'new_file.txt' is removed from the 'parsing_errors' folder.
    - The function creates an empty folder, replacing the removed file.
    - The returned string path matches the path of the newly created empty folder.
    """
    new_folder_path = Path(tmp_path) / "parsing_errors"
    new_folder_path.mkdir()

    with open(f"{new_folder_path}/new_file.txt", "w") as f:
        f.write("some_text")

    str_path: str = prepare_error_folder(str(tmp_path))

    assert not Path(f"{new_folder_path}/new_file.txt").exists()
    assert str_path == str(new_folder_path)
    assert new_folder_path.exists()


def test_xml_writer_error_dump(tmp_path, mocker):
    mocker.patch.object(XMLWriter, "custom_item_func", side_effect=lambda p: {"new_tag": "tag"}.get(p, "item"))
    data = {"new_tag": ["ok", "\uD800"]}
    xml_file = io.StringIO()
    writer = XMLWriter()

    mocker.patch("mcod.core.utils.prepare_error_folder", return_value=str(tmp_path))

    with pytest.raises(_XML_EXC):
        writer.save(xml_file, data, language_catalog_path=str(tmp_path))

    dump = tmp_path / "data.json"
    assert dump.exists()
    assert dump.read_text().startswith("{")
