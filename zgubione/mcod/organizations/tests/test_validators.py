import pytest
from django.core.exceptions import ValidationError

from mcod.organizations.model_validators import validate_eda


class TestElectronicDeliveryAddressValidator:
    def test_invalid_checksum_number_of_eda(self):
        electronic_delivery_address = "AE:PL-11111-22222-AAAAA-33"
        with pytest.raises(ValidationError) as e:
            validate_eda(electronic_delivery_address)

        assert "Podany adres nie jest zgodny z formatem adresu do doręczeń " "elektronicznych." == e.value.message

    @pytest.mark.parametrize(
        "invalid_eda_format",
        [
            "AE:PL-BBBBB-22222-AAAAA-33",
            "AE:PL-22222-BBBBB-AAAAA-33",
            "AE:PL-11111-22222-AAAAA-ZZ",
            "11111-22222-AAAAA-33",
            "AE-11111-22222-AAAAA-33",
            "PL-11111-22222-AAAAA-33",
            "AE:PL1111122222AAAAA33",
            "AEPL-11111-22222-AAAAA-33",
            "AE-PL-11111-22222-AAAAA-33",
            "AE:PL-11111-22222-abcde-33",
            "AE:PL-98765-43210-SFVYC-1912",
            "AE:PL-98765-43210-SFVYC-19AA",
            "AE:PL-98765-43210-SFVYC-19-12",
            "AE:PL-98765-43210-SFVYC-19-AA",
            "EA:PL-98765-43210-SFVYC-19",
            "AE:IT-98765-43210-SFVYC-19",
            "",
            " ",
        ],
    )
    def test_invalid_format_of_eda(self, invalid_eda_format: str):
        with pytest.raises(ValidationError) as e:
            validate_eda(invalid_eda_format)

        assert "Podany adres nie jest zgodny z formatem adresu do doręczeń " "elektronicznych." == e.value.message

    @pytest.mark.parametrize(
        "valid_eda",
        [
            "AE:PL-98765-43210-SFVYC-19",
            "AE:PL-42341-70981-HJUID-18",
            "AE:PL-89273-09291-JIEWJ-33",
            "AE:PL-00123-98212-POWER-36",
            "AE:PL-99911-21037-JPDGD-23",
        ],
    )
    def test_eda_format_and_checksum_validation(self, valid_eda: str):
        validate_eda(valid_eda)
