# Wzorcowy Schemat Danych: Rzeczy Znalezione (Open Data Standard)

Każdy rekord o rzeczy znalezionej powinien zawierać następujące pola:

1. **name** (Tekst): Krótka nazwa przedmiotu.
2. **category** (Słownik): Jedna z wartości:
   - keys (Klucze)
   - electronics (Elektronika)
   - clothing (Ubranie)
   - wallets/money (Portfel/pieniądze)
   - jewellery (Bizuteria)
   - documents (Dokumenty)
   - animal (Zwierzeta)
   - other (Inne)
3. **found_date** (Data, ISO 8601): Format YYYY-MM-DD.
4. **location_city** (Tekst): Nazwa miejscowości.
5. **location_description** (Tekst): Szczegółowy opis miejsca (np. park, autobus).
6. **image** (URL): Link do zdjęcia (opcjonalnie).
7. **contact_info** (Tekst): Instrukcja odbioru dla obywatela.
8. **status** (Słownik): Jedna z wartości:
   - lost (Zgubiony)
   - found (Znaleziony)
   - claimed (Odebrany)
9. **description** (Tekst): Opis przedmiotu.
