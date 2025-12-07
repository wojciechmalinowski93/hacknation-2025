from django.db.models import Max

from mcod.special_signs.models import SpecialSign


class VocabEntry:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class SpecialSignVocab:
    version = "2022.05.01"
    label_pl = "Znak umowny"
    label_en = "Special sign"

    def __init__(self):
        from mcod.core.api.rdf.profiles.dcat_ap_pl import VOCABULARIES

        self.url = VOCABULARIES["special-sign"]
        qs = SpecialSign.objects.filter(status="published")
        vocab_modified = qs.aggregate(Max("modified"))["modified__max"]
        self.version = f"{vocab_modified:%Y.%m.%d}" if vocab_modified else "2022.05.01"
        self.entries = {}
        for sign in qs:
            self.entries[str(sign.id)] = VocabEntry(
                vocab_url=self.url,
                name_pl=sign.name_pl,
                name_en=sign.name_en,
                notation=sign.symbol,
                url=f"{self.url}/{sign.id}",
                description_pl=sign.description_pl,
                description_en=sign.description_en,
            )
