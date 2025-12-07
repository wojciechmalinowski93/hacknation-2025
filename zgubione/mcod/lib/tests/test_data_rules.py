from mcod.lib.data_rules import boolean_rule, krs_rule, nip_rule, numeric_rule, pna_rule, regon_rule


class TestRulesTemplates:

    def test_boolean_tmpl(self):
        result = boolean_rule("col")
        expected = """
def col = doc['col'].value;


if ( col instanceof boolean ) {
  return false
} else {
    if ( col instanceof String) {
        if ( col == "True" || col == "False" ) {
            return false
        } else {
            return true
        }
    }
    return true
}

"""
        assert result == expected

    def test_krs_rule_tmpl(self):
        result = krs_rule("col1")
        expected = """
def col1 = doc['col1'].value;


if (col1.toString().length() == 10) {
    return false
} else {
    return true
}


"""
        assert expected == result

        result = krs_rule("col1.keyword")
        expected = """
def col1 = doc['col1.keyword'].value;


if (col1?.length() == 10) {
    def result = false;
    try {
        def res = Float.parseFloat(col1);
    } catch (Exception e) {
        result = true;
    }
    return result
} else {
    return true
}


"""
        assert expected == result

    def test_nip_rule_tmpl(self):
        result1 = nip_rule("col1")
        expected1 = """
def col1 = doc['col1'].value;


if (col1.toString().length() == 10) {
    return false
} else {
    return true
}


"""
        result2 = nip_rule("col1.keyword")
        expected2 = """
def col1 = doc['col1.keyword'].value;


if (col1?.length() == 10) {
    def result = false;
    try {
        def res = Float.parseFloat(col1);
    } catch (Exception e) {
        result = true;
    }
    return result
} else {
    return true
}


"""
        assert result1 == expected1
        assert result2 == expected2

    def test_numeric_rule_tmpl(self):
        result = numeric_rule("col1")
        expected = """
def col1 = doc['col1'].value;

if (col1 instanceof int || col1 instanceof long || col1 instanceof double || col1 instanceof float) {
    return false
} else {
    def result = false;
    try {
        if (col1!=null) {
            def res = Float.parseFloat(col1);
        }
    } catch (Exception e) {
        result = true;
    }
    return result
}

"""
        assert expected == result

    def test_pna_rule_tmpl(self):
        result = pna_rule("col1")
        expected = r"""
def col1 = doc['col1'].value;

if (col1 instanceof String) {
    if (col1 ==~ /\d\d-\d\d\d/) {
        return false
    } else {
        return true
    }
} else {
    return true
}

"""
        assert expected == result

        result = pna_rule("col1.keyword")
        expected = r"""
def col1 = doc['col1.keyword'].value;

if (col1 instanceof String) {
    if (col1 ==~ /\d\d-\d\d\d/) {
        return false
    } else {
        return true
    }
} else {
    return true
}

"""
        assert expected == result

    def test_regon_rule_tmpl(self):
        result = regon_rule("col1")
        expected = r"""
def col1 = doc['col1'].value;

col1 = col1.toString();
if (col1 ==~ /\d{9}|\d{14}/) {
    return false
} else {
    return true
}

"""
        assert expected == result
