Feature: Dataset licenses

  Scenario Outline: Licenses endpoint returns data for various license names
    When api request path is <request_path>
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field data/attributes/link
    And api's response body has field data/attributes/secondLink

    Examples:
    | request_path         |
    | /licenses/CC0        |
    | /licenses/CCBY       |
    | /licenses/CCBY-SA    |
    | /licenses/CCBY-NC    |
    | /licenses/CCBY-NC-SA |
    | /licenses/CCBY-ND    |
    | /licenses/CCBY-NC-ND |

  Scenario: Licenses endpoint returns 404 for invalid name
    When api request path is /licenses/INVALID
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Licenses endpoint returns valid data
    When api request path is /licenses/CC0
    And send api request and fetch the response
    Then api's response body field data/attributes/link is https://creativecommons.org/publicdomain/zero/1.0/legalcode.pl
    And api's response body field data/attributes/secondLink is https://creativecommons.org/publicdomain/zero/1.0/legalcode.pl
    And api's response body field data/attributes/description/name is Brak praw autorskich.
    And api's response body field data/attributes/description/description is Osoba, która opatrzyła utwór tym oświadczeniem, przekazała go do domeny publicznej, zrzekając się wykonywania wszelkich praw do utworu wynikających z prawa autorskiego, włączając w to wszelkie prawa powiązane i prawa pokrewne, w zakresie dozwolonym przez prawo, na obszarze całego świata. Możesz zwielokrotniać, zmieniać, rozpowszechniać i wykonywać utwór, nawet w celu komercyjnym bez pytania o zgodę.

  Scenario: Licenses endpoint returns valid data in english
    When api request path is /licenses/CC0
    And api request language is en
    And send api request and fetch the response
    Then api's response body field data/attributes/link is https://creativecommons.org/publicdomain/zero/1.0/legalcode
    And api's response body field data/attributes/secondLink is https://creativecommons.org/publicdomain/zero/1.0/deed
    And api's response body field data/attributes/description/name is No Copyright
    And api's response body field data/attributes/description/description is The person who associated a work with this deed has dedicated the work to the public domain by waiving all of his or her rights to the work worldwide under copyright law, including all related and neighboring rights, to the extent allowed by law. You can copy, modify, distribute and perform the work, even for commercial purposes, all without asking permission.
