import re


class VocabEntry:
    def __init__(self, description_pl="", description_en="", **kwargs):
        self.description_pl = re.sub("[\n ]+", " ", description_pl).strip()
        self.description_en = re.sub("[\n ]+", " ", description_en).strip()
        for key, value in kwargs.items():
            setattr(self, key, value)


class OpennessScoreVocab:
    version = "2022.05.01-0"
    label_pl = "Poziom otwartości"
    label_en = "Openness score"

    def __init__(self):
        from mcod.core.api.rdf.profiles.dcat_ap_pl import VOCABULARIES

        self.url = VOCABULARIES["openness-score"]
        self.entries = {
            "1-star": VocabEntry(
                vocab_url=self.url,
                name_pl="1 gwiazdka",
                name_en="1 star",
                notation="*",
                url=f"{self.url}/1-star",
                description_pl="""
                        Pierwszy poziom otwartości danych. Dane w dowolnym formacie, udostępniane bez ograniczeń licencyjnych.
                        Mogą to być pliki JPEG z zeskanowanymi dokumentami, wygenerowane z różnych programów pliki PDF lub pliki
                        tekstowe zawierające dane nieustrukturyzowane albo o strukturach niejednorodnych. Większość ludzi może je
                        odczytać, ale jakiekolwiek dalsze ich wykorzystywanie wymaga dodatkowej pracy, polegającej na
                        zidentyfikowaniu, odczytaniu i przeniesieniu danych (często ręcznie bądź ze wspomaganiem programów
                        typu OCR).
                        """,
            ),
            "2-stars": VocabEntry(
                vocab_url=self.url,
                name_pl="2 gwiazdki",
                name_en="2 stars",
                notation="**",
                url=f"{self.url}/2-stars",
                description_pl="""
                        Drugi poziom otwartości danych. Dane spełniają pierwszy poziom otwartości oraz mają już określoną
                        strukturę, którą można odczytać komputerowo, np. przez zastosowanie pliku w formacie arkusza
                        kalkulacyjnego lub edytora tekstu. Nie są to zeskanowane obrazy w niedającej się przeszukiwać formie.
                        Dane te są w formacie zamkniętym (własnościowym), dla którego stosowanie w oprogramowaniu jest
                        ograniczone przez restrykcje patentowe, licencyjne lub podobne.
                        """,
            ),
            "3-stars": VocabEntry(
                vocab_url=self.url,
                name_pl="3 gwiazdki",
                name_en="3 stars",
                notation="***",
                url=f"{self.url}/3-stars",
                description_pl="""
                        Trzeci poziom otwartości danych. Dane spełniają drugi poziom otwartości oraz są w otwartym formacie, ale
                        ich zrozumienie na potrzeby przetwarzania maszynowego wymaga każdorazowej analizy danych i ustalenia bądź
                        odnalezienia w dokumentacji, jeżeli taka istnieje, znaczeń poszczególnych pól. Czy „nazwisko" oznacza samo
                        nazwisko, czy imię i nazwisko? Czy „kod" to kod pocztowy, czy terytorialny? Czy „odległość" jest podana w
                        metrach, czy w kilometrach? Czy „1/12/2018" to pierwszy grudnia, czy dwunasty stycznia? Dane udostępniane
                        są w niezastrzeżonym formacie.
                        """,
            ),
            "4-stars": VocabEntry(
                vocab_url=self.url,
                name_pl="4 gwiazdki",
                name_en="4 stars",
                notation="****",
                url=f"{self.url}/4-stars",
                description_pl="""
                        Czwarty poziom otwartości danych. Dane spełniają trzeci poziom otwartości oraz publikowane są w formacie
                        umożliwiającym oznaczenie ich struktury znaczeniowej. Wejście na czwarty poziom otwartości pozwala
                        jednoznacznie określić znaczenie udostępnianych danych. Technicznym sposobem wyrażania takiego znaczenia
                        w sposób zrozumiały dla maszyn jest identyfikacja konkretnych właściwości danych za pomocą zrozumiałych
                        dla maszyny URI zgodnie z modelem RDF (model opisu danych).
                        """,
            ),
            "5-stars": VocabEntry(
                vocab_url=self.url,
                name_pl="5 gwiazdek",
                name_en="5 stars",
                notation="*****",
                url=f"{self.url}/5-stars",
                description_pl="""
                        Piąty poziom otwartości danych. Dane spełniają czwarty poziom otwartości oraz zawierają połączenia
                        strukturalne online do innych zbiorów informacji. Piąty poziom dodatkowo ułatwia przetwarzanie – jawnie
                        wskazuje relacje między danymi w formie linków. Dzięki temu możliwe jest odnajdywanie połączeń między
                        różnymi zbiorami danych.
                        """,
            ),
        }
