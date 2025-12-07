from datetime import datetime, timedelta
from typing import Dict, Type

import jwt
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from logingovpl.objects import LoginGovPlUser
from requests import Request

from mcod.api import ApiApp, get_api_app
from mcod.core.api.middleware_loader import middleware_loader

User = get_user_model()


@pytest.fixture
def test_api_instance() -> ApiApp:
    middlewares = middleware_loader()
    return get_api_app(middleware=middlewares)


@pytest.fixture
def logingovpl_user() -> LoginGovPlUser:
    """Returns a LoginGovPlUser instance."""
    return LoginGovPlUser("first_name", "last_name", "date_of_birth", "pesel")


@pytest.fixture
def expired_jwt_token() -> str:
    expiration_time = datetime.utcnow() - timedelta(days=1)
    jwt_token = jwt.encode(
        {"exp": expiration_time},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHMS[0],
    )

    return jwt_token.decode()


class TestRequest(Request):
    """Test request class."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class TestResponse:
    """Test response class."""

    def __init__(self, **kwargs):
        self.content = kwargs.get("content")


@pytest.fixture
def mocked_request_object() -> Type[TestRequest]:
    """Returns a mocked request object."""
    return TestRequest


@pytest.fixture
def response_data_from_logingovpl() -> Dict[str, str]:
    return {"encoding": "utf-8", "SAMLart": "some_saml_art", "RelayState": "some_relay_state"}


@pytest.fixture
def resolve_artifact_response_auth_failed() -> bytes:
    binary_value = b'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"/><soap:Body><saml2p:ArtifactResponse xmlns:alg="urn:oasis:names:tc:SAML:metadata:algsupport" xmlns:coi-extension="http://coi.gov.pl/saml-extensions" xmlns:coi-naturalperson="http://coi.gov.pl/attributes/naturalperson" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:dsig11="http://www.w3.org/2009/xmldsig11#" xmlns:eidas="http://eidas.europa.eu/saml-extensions" xmlns:kirwb="http://wb.kir.pl/saml-extensions" xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" xmlns:mdattr="urn:oasis:names:tc:SAML:metadata:attribute" xmlns:naturalperson="http://eidas.europa.eu/attributes/naturalperson" xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion" xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:xenc="http://www.w3.org/2001/04/xmlenc#" xmlns:xenc11="http://www.w3.org/2009/xmlenc11#" ID="ID-6f971630-b485-4366-a9ee-f0b111547eff" InResponseTo="ID-2062b5c4-87ac-482a-af14-f94e0197dab3" IssueInstant="2024-07-12T08:34:30.235Z" Version="2.0"><saml2:Issuer>int.login.gov.pl</saml2:Issuer><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"/><ds:Reference URI="#ID-6f971630-b485-4366-a9ee-f0b111547eff"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/><ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"><InclusiveNamespaces xmlns="http://www.w3.org/2001/10/xml-exc-c14n#" PrefixList="ds saml2 saml2p xenc"/></ds:Transform></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>k9BVQslQZ2lhrvhEWeBdlK1cK2fRqfBnxrrG+ODjsLg=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>h7XSl9d06uweAtKuqVx32pYXGp/qihgVTN4vDedyzI9gL8r1voGFar3CmO8uCS/bRekoS8LAFLPi6rHqujG6KQ==</ds:SignatureValue><ds:KeyInfo><ds:X509Data><ds:X509Certificate>MIIELzCCAhegAwIBAgIEab/egzANBgkqhkiG9w0BAQsFADCBlDELMAkGA1UEBhMCUEwxFDASBgNVBAgTC21hem93aWVja2llMREwDwYDVQQHEwhXYXJzemF3YTEMMAoGA1UEChMDQ09JMQwwCgYDVQQLEwNTVUExEDAOBgNVBAMMB1JPT1RfV0sxLjAsBgkqhkiG9w0BCQEWH3NlYmFzdGlhbi5ub3dha293c2tpQGNvaS5nb3YucGwwHhcNMjAwOTI5MTMyMTAwWhcNMjUwODE4MTMyMTAwWjCBljELMAkGA1UEBhMCUEwxFDASBgNVBAgTC21hem93aWVja2llMREwDwYDVQQHEwhXYXJzemF3YTEMMAoGA1UEChMDQ09JMQwwCgYDVQQLEwNTVUExEjAQBgNVBAMMCVdLX1NJR19FQzEuMCwGCSqGSIb3DQEJARYfc2ViYXN0aWFuLm5vd2Frb3dza2lAY29pLmdvdi5wbDBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABPIt7gV8z1DxngmiMygV0jlXa00julx1RbP/s/HniqWceV+ePhdXA6+vTIep7itzaLUx6nMRvWxrMj9JcKujWBqjUDBOMAkGA1UdEwQCMAAwCwYDVR0PBAQDAgbAMDQGA1UdHwQtMCswKaAnoCWGI2h0dHA6Ly8xNzIuMjQuNjEuMjEvQ1JML1JPT1RfV0suY3JsMA0GCSqGSIb3DQEBCwUAA4ICAQChdcOues2Nk8Qs4qvJ23D/R8KKAcKLRK5sst6IiG8L8arUyX9cLGLFSsQ2QhJ9aNvHEABhctF47DoDPxKW+UwB+ylO9rIQDYlx++bp3kl67UQoC3KYkLV+Hwbdpfsm92/g5obdUyzwBHo6JxAAuFV+zzYSgAthcGD+kUf6SsbnbJaVLN2sSXHk23AfyOByu6fBN6JT6eAW0qfSM7HpuaVOrT9W9IbBvehHlRsWqQgyKSPSltykwrF3+9Qw3LyqtDN7wNgG29J++/AFkcz4b8xBrJDBQXPZG/QpfxkpheUhNmo8PLKfNpEEWU/icsEYNh/hMWqeNSqxMIKcbphJ6B0s33w4dy+qm1uaZp/2sk4hmHJvmmlukImKwiNeJC7NOkIYt7oQL4YGIWxfw/ugWibT9FdjaE+sUpI+o2GW2vWCNiZZbeLsVTmjysDBM1kIYpzG+hmoWY5mVdDRtGo63RyiMBF6KJcg5jnkL2uqr2xCmfU8zj6ryBd/LzMFK9a4gP6t01obaco8aMjnL0Uigefg2MbWwdv7Ic6JyaK0aMBgkoRGrLxFzpfvav7uGD2csj9LY32y5vkzniAkZk6GsZtXXvMwdQvHvQhkALP5ZiSpBxM35mAU4CYbaD3TtpZE4BfMJ9PA1N6kmgkVQUQvQWI6GdaSvd7j/eBjf8dS0z3lTQ==</ds:X509Certificate></ds:X509Data></ds:KeyInfo></ds:Signature><saml2p:Status><saml2p:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:AuthnFailed"/></saml2p:Status><saml2p:Response ID="ID-aea57430-01c6-4b5d-93d8-ad74c51e7b51" InResponseTo="ID-d4a07363-aebe-496f-9243-3cc346c3ceb6-LINK-1867" IssueInstant="2024-07-12T08:34:30.235Z" Version="2.0"><saml2:Issuer>int.login.gov.pl</saml2:Issuer><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"/><ds:Reference URI="#ID-aea57430-01c6-4b5d-93d8-ad74c51e7b51"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/><ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"><InclusiveNamespaces xmlns="http://www.w3.org/2001/10/xml-exc-c14n#" PrefixList="ds saml2 saml2p xenc"/></ds:Transform></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>0VtMW7Wl4PdnMBgAwA2tlnHcP+oUDALaTViiYZL11KM=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>QwRjyvvQkcHQS7cKMF4m75n8frx6DZOokLd3a0tZwlwlzKCHMnw2MYUnNW6O5ItJj5mntJpHxgk44mIWsbHkFg==</ds:SignatureValue><ds:KeyInfo><ds:X509Data><ds:X509Certificate>MIIELzCCAhegAwIBAgIEab/egzANBgkqhkiG9w0BAQsFADCBlDELMAkGA1UEBhMCUEwxFDASBgNVBAgTC21hem93aWVja2llMREwDwYDVQQHEwhXYXJzemF3YTEMMAoGA1UEChMDQ09JMQwwCgYDVQQLEwNTVUExEDAOBgNVBAMMB1JPT1RfV0sxLjAsBgkqhkiG9w0BCQEWH3NlYmFzdGlhbi5ub3dha293c2tpQGNvaS5nb3YucGwwHhcNMjAwOTI5MTMyMTAwWhcNMjUwODE4MTMyMTAwWjCBljELMAkGA1UEBhMCUEwxFDASBgNVBAgTC21hem93aWVja2llMREwDwYDVQQHEwhXYXJzemF3YTEMMAoGA1UEChMDQ09JMQwwCgYDVQQLEwNTVUExEjAQBgNVBAMMCVdLX1NJR19FQzEuMCwGCSqGSIb3DQEJARYfc2ViYXN0aWFuLm5vd2Frb3dza2lAY29pLmdvdi5wbDBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABPIt7gV8z1DxngmiMygV0jlXa00julx1RbP/s/HniqWceV+ePhdXA6+vTIep7itzaLUx6nMRvWxrMj9JcKujWBqjUDBOMAkGA1UdEwQCMAAwCwYDVR0PBAQDAgbAMDQGA1UdHwQtMCswKaAnoCWGI2h0dHA6Ly8xNzIuMjQuNjEuMjEvQ1JML1JPT1RfV0suY3JsMA0GCSqGSIb3DQEBCwUAA4ICAQChdcOues2Nk8Qs4qvJ23D/R8KKAcKLRK5sst6IiG8L8arUyX9cLGLFSsQ2QhJ9aNvHEABhctF47DoDPxKW+UwB+ylO9rIQDYlx++bp3kl67UQoC3KYkLV+Hwbdpfsm92/g5obdUyzwBHo6JxAAuFV+zzYSgAthcGD+kUf6SsbnbJaVLN2sSXHk23AfyOByu6fBN6JT6eAW0qfSM7HpuaVOrT9W9IbBvehHlRsWqQgyKSPSltykwrF3+9Qw3LyqtDN7wNgG29J++/AFkcz4b8xBrJDBQXPZG/QpfxkpheUhNmo8PLKfNpEEWU/icsEYNh/hMWqeNSqxMIKcbphJ6B0s33w4dy+qm1uaZp/2sk4hmHJvmmlukImKwiNeJC7NOkIYt7oQL4YGIWxfw/ugWibT9FdjaE+sUpI+o2GW2vWCNiZZbeLsVTmjysDBM1kIYpzG+hmoWY5mVdDRtGo63RyiMBF6KJcg5jnkL2uqr2xCmfU8zj6ryBd/LzMFK9a4gP6t01obaco8aMjnL0Uigefg2MbWwdv7Ic6JyaK0aMBgkoRGrLxFzpfvav7uGD2csj9LY32y5vkzniAkZk6GsZtXXvMwdQvHvQhkALP5ZiSpBxM35mAU4CYbaD3TtpZE4BfMJ9PA1N6kmgkVQUQvQWI6GdaSvd7j/eBjf8dS0z3lTQ==</ds:X509Certificate></ds:X509Data></ds:KeyInfo></ds:Signature><saml2p:Status><saml2p:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:AuthnFailed"/></saml2p:Status><saml2:EncryptedAssertion><xenc:EncryptedData Id="_31dda0dc5cb181d4ed4932119849deef" Type="http://www.w3.org/2001/04/xmlenc#Element"><xenc:EncryptionMethod Algorithm="http://www.w3.org/2009/xmlenc11#aes256-gcm"><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/></xenc:EncryptionMethod><ds:KeyInfo><xenc:EncryptedKey Id="_fc0b7e93fa2ef504fc9c751237124aff"><xenc:EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#kw-aes256"/><ds:KeyInfo><xenc:AgreementMethod Algorithm="http://www.w3.org/2009/xmlenc11#ECDH-ES"><xenc11:KeyDerivationMethod Algorithm="http://www.w3.org/2009/xmlenc11#ConcatKDF"><xenc11:ConcatKDFParams AlgorithmID="0000002A687474703A2F2F7777772E77332E6F72672F323030312F30342F786D6C656E63236B772D616573323536" PartyUInfo="00000010696E742E6C6F67696E2E676F762E706C" PartyVInfo="0000000B6F74776172746564616E65"><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/></xenc11:ConcatKDFParams></xenc11:KeyDerivationMethod><xenc:OriginatorKeyInfo><ds:KeyValue><dsig11:ECKeyValue><dsig11:NamedCurve URI="urn:oid:1.2.840.10045.3.1.7"/><dsig11:PublicKey>BJC9Jc+ad2r8922XJwPup+zXvwz+HDJjowEDHmS9VixN1EXK9Il7mMywUvdZWaeeabFN7z2Z9ghp6kOk/FF2SWk=</dsig11:PublicKey></dsig11:ECKeyValue></ds:KeyValue></xenc:OriginatorKeyInfo></xenc:AgreementMethod></ds:KeyInfo><xenc:CipherData><xenc:CipherValue>rPOmZ3fglrgRT7V2qMKeXWQhRIUBeQb+d8WTtyOO5l6Xt2PvHkV8zg==</xenc:CipherValue></xenc:CipherData></xenc:EncryptedKey></ds:KeyInfo><xenc:CipherData><xenc:CipherValue>sLrFX9zfQc9XxPtO4mBXcl6m9n731lXJ9A8UTZnRceCPlIsAqu9rXeaSxuqzAEXp63XCyPEIEqbubCIbXmNHQpsv6FnJeHVEzNy1WaEOsbiJB9MY89PQCYTgYn1Y7bqGYM9gvAY+mIJYoBlSfkUOitMbotzVC7y3JVgA3L9TLEc6mpNRV2TYclVz8pI89HRFwPy7ZM1bodQSxtjkr0dqAlW4GPg+ZOeOGfyPF6PqgdXAqGL0bV3egiLe+T2CewxweR1c9iliX9HNF6CQ/uw/zuRQrWjbELhqQyt75Eo9P9Vbin64xFgxVDoDlmzHwN0T6aImpxuGCNVd6+A5V+llDsn8GoyCIpuQ0rMFIVtJ/H14YehA5wYpSkht2c/Wbrrb/9B+UP2hVvtLw03nE0dMUYej0IltkAE3ebuvKQtMfHeWch7xw8KAHQsYgPbiGCKauSvR2JRADsUqqlc96OOlc0ScefRCyrio3a7tEu2C2HJacavwI9p8GzTUOtWjBwxRdkQE+JxMw+0WZimbXGcRC28Y/Z7dGCa47dzPEGrD9i+Qr9Uwd/L+8BPuJnuaQHdsICoJLO+21sxPMGDSwW4awummUB2WQa4vACkYjYEPZeEWUG+m97n+9B6hy+bZXHT77EFQXz/Qcr4MYCU9BPu0HodAHwg4Wxg74hJwXcmGuKZpttGfpKwniJ//+ZERCwrXVdfugjKvDZtx/UDpzOA4HPDhDJp5BxRs7/h/OzeLmFR5nA3+6JSdEOo6gLN5vofHMCcFfLC7a0H6J5fcvIbekgtG3eyK/2IO3sSgaHyOGyTccY7rR0oIJmRgSQi6NynSqQZDH10HZAmz+gLcJB+dxUx7aytX9EWcreYH10rT0LAI/4oaqsD8DDLIzEPbr+dhbTAYbd61XoOru361d4hr/p1zD4cIhm3ZmOcSgaTPTg1LED5VkzRRVGqPDERWXTux6YJ+sxPZvmYdoEhjGjVQpaScoJosAlFZE21yxUqN1DVRX5pOP5u/r+ItPWyOdfRAveoO2XZJH/73uLaNxaYbXrrS1e9RmcIfxrAGWjJi/pSp+oN+36lwdPhS3nZIqS175DZpG2rsRr3HA/R5UKM1qpLJ4HeowTqdOsIs7N83YkHSAwrNn5jqpDOsTskPNdHNe2Yu1gK18OWRJcrdY7EZFh1YYMFquyfDph2NaDo2mdPvJO5Z8Pgs7WW2LsV3lZnq7QWZ/2ulbG8nIHobpAJAce3oMwgu6X9h1Pd2p3yKEAB9EP4PvZdH0no4Kho2z4LvhRq+SazBvP+KCILoMQL8fWNMMa23C2mDemJsP0Xomeo1IuQjzCC/rO4QKehxiYO9qMXvIvyyOC5mwWLWckTPBLlKnHUjXm8Z/f2aPyZE54wa0Yz4GhH4lkqU8O/d0XKcJHrKK58npHWKxm8OEJXaVR7PC134xJEsKbvjEFOXJnvr7kfYDNcw0IQfBTl9MXtsCM5ascKvb+8xnAke3+dpS8v0vgQ82WBF9B8VHOFoFQQ9sNYpCLvoBECUUMLeK2x/f7sPmlxFpqVo/veIYPCGBQT05stHxB/ozrPVxXyG2eQl8iCG+Xs/wLUzCKSZLu2KqIkFEFa13qVUj0WFQ9YJfxWb1bNBvp2cYyS2+zUj7sMR55kq+GFZzh8j4ycUeZplynXbcYPDQiaXgTz7F2IhItkrlHCC4YzgDabjr7Cdvt/kHsyfUtTYOBaq5eu574GkP7Yo+WVo+tzHv5da3xTMrPO1Yc9ZkSnR4FqzPWkfAEeJ01JVpBq75Z34dJeo2Hc7i4UerMaImuS0X/LhdxYjkINgI9qRdByVQprPLs0pGgbZVPt69sNEmVn3VKZj02qbrE7mV4MQyY+Z0UCR/H9Sh8Ds6qEiJ5Jgvp86418eOrbddEF0fq2GJzP4m9qgQYuu5vculATvWE4ctWPNp/2ZDBOn2jU9k0UYuJAWshZszmg7ybOMwJCLgH8yGFWFk76sJvd6GMJKnYOdscZcW83IRoWp4ymQPxIrf1Lmw4aJyZPxjlKGxmDz40P50ryHsnjLNtR79E9eARqVaglWu1beFXmwcpClD1jDxkYGMHDJG9GWCRF8Oti9X/f20epzrHRmL1wk23i2S3FPMYNPam07YVA4Q9/pryMkcMKr5XrnrPa0Wk8ZppHfigs3GROhbTEGz8akxSKNZwgwTRqyaJmjWxr83HDRhH8+cLZNHoFMKYeD7JgeoZJ8lnunWHAC27DYp5Yr2sRKpjj67X4r6wJ6sv5Dc3mQc0MauZFoFz+0X+/22Q3ddyF//B2RNC7KWJDcVKusy09tuAEb2DZvHYreTGjkaoUA2LWB820+sHtdvJ9MUg16Yb3qrgqDSNQthyuZxEF/5t7TWtAMPfv6fljU4NS5GZrBCtPErQ/nFHseQtEGCmTDs3pYWzvolzDLvNUPtamWs4BOh6GBVjqK6ItzsJeG8OwuZwXWA49Qx2djkayNPEbjPQtwuH/YXS3rx9L2B+fyF0n5JdaMc75FGBmOHSSQDs6jaFpIu4r4atfHCjNPxMsT9XW4o9oRJ8NaAyLrZ4i0dTs1JeZdn7n858NgGfoUBS5+t2V4Xbly/y590WwEKCy+trTShqQ8d27eSy/7LzqNpi/g7neCqtXXMQp5Oh+GgFipJKnLAQE6RwixZAhROBnq4UWMWloQTfaoUGH6gRRHxyegBSzEkYFDuVgXEoVtSI/8EvTuy/XPwe51L6/svvthbVrz9u3iQCGe5g2zIphYqnnLHmiOQq4afAcnT+DwuXwWswCJ+Rmn+e+XFhT4UeTijccpFJQ0oA/30EImLU2aSerCwlzzykLdUcnydB25vwUiY/+qOZYOCL9SX5s8etEJwdAN8BxibtV2DfquN/h/2932mBrqEHc4uZoGmDfeSe7w4gM4JGTym8JgXI9JcDv2N0zZVCgTxGnivySFmvEcKS3A1wWjzbYbDf89oK3f0DfzDA0GjOIfuaysL+ZOyZ5FET9nnSL2WAlpXbqxSGG0JZll1kClAiWHZuEHWH7m+vipVNDqM1PYsokhf2XcBaSoUENB1fldKLtCwUaojsv3pnbiRo15mAluXnffiICug7FQB12lkfMONSnEwAYgNoPqCvxHOzZ4C/qaTIhbN0hVn67j48gWBW2geGBRX5BYsyZ5/UaR0AWEHsg0CwH/EW0o6M4NEsn0T2bovFokueJCH10e4Fw/LflAiEY8qZf6t0bmuaEHzeCz7m/POsxDOJx1S2arNwKBcSd/+PUE5ksIdU1DIZNmDcKT5EcMKxov6mnibjJhmQFLucBbPzLWQy9dGW/WGHB5WA75q7h4eHYC4UgVJx69WSMf3sGDWqabS0CYit/v2HWlxjcWNJwnYbW7jRvzFvgDN6tcgMQAEbuRIv9MH9h0SDxEMa6bkC146uuarW4Iu7hpshieAjgwTyG5esnf1j71nSabgBC9Y/oYSw9CErbr6pwi0aXy3JLbUpThiClo81ijtLd2ICfgdKGQQ6ZAFiiY7LDVfZsV1FrEfQuBptbnp69CFY20HqqMi2jiusMGnHcN1Pulwx8Z6yYs4HgniZX5yEyeuXodh62IKtCLqtsnOibiyQKgCZM2XFmEkrh0Cv9fXxvz8WOGTT0Mc16+Wv83ulDAYHWdhXEe0WnKdpUI/KoE29YpF+8g6xZ9Ad2vQiz2tT9V2MJuC/i2seqF7fuHuF0UU8hwiYhQR3Qx/Fok8yu+moGaljJdw/EG4QsZWAkvgRcy0ZkFec9lydRiBpskodrbXl8o/z3UVw24/In2+nv7ucckXS36hFsL7MUbr+lKHplxNU/hj5EJ/I8S4EvUPd0tXanxPE1ZzXbdIixs9rhGQFJsZKkkvnlTfT/WArNMrTr1vmUW/BwLVMTL+y7QWpDJIQLdAicAhUcZLYvbfXwFjoGWpBTCbQQprqXbEekvwjWdna4QKVtmM+0uSX4jdL4fpwnvflhEyQHuPp+724jes0oYB8aDWsfbyjX7TYaCOQJ+XCDhYAgoXR7ZKPO0eLCS7hGCEq9YJKd3jn9AY/HdIHYaQkxuROJoBuiixiZ/dkniSccGVa4uXjEttMY02zjFyfYO0kh+UJnmeMLavojJP31x8qT4LMcUQJNILr9eMoRO08DKyXX5YZgD2qmdA/nSYPfIu+Hu5FUX8JSUE9KmA/uTJsD1lzOqo7ABav1yaIoXbhyG8mvowRWhDEupiZ279RUcR6hr/BmCjiDTqOR1IQgIv+d5B9Gtz7WQh549ZS+0WKtZlOwyRJxx4bb8eZBJg+4SjWyJeTm+FZNKd1LyTviL7QWdcNmPLq5tFSVcQhtR1w4SJKtlf+VGHSlTdP3OUOHNeowd2x84xjmxX6yRAleyLWVtXJbx3N3XocB0aWROGBkGM3nG49V9bT7s8myHTKkP/kSxSLw1/RoU3ZxTk9EeAAoZM2l8QFVJoOTDfZ0FVw==</xenc:CipherValue></xenc:CipherData></xenc:EncryptedData></saml2:EncryptedAssertion></saml2p:Response></saml2p:ArtifactResponse></soap:Body></soap:Envelope>'  # noqa: E501
    return binary_value


@pytest.fixture
def api_with_routes_for_test(test_api_instance) -> test_api_instance:
    from mcod.core.tests.fixtures.api_test_views import ApiTestView

    routes = [
        ("/test_endpoint", ApiTestView()),
    ]
    routes.extend(list(map(lambda x: ("/{api_version}" + x[0], *x[1:]), routes)))
    test_api_instance.add_routes(routes)
    return test_api_instance
