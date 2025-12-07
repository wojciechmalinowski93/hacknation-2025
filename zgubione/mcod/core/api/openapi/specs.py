import markdown2
from apispec import APISpec

from mcod.core.api.openapi.plugins import MCODPlugin
from mcod.core.api.versions import DOC_VERSIONS


def get_spec(version=None):
    """
    Welcome to the **DANE.GOV.PL API**,
    the source of reliable, constantly updated data,
    made available free of charge for re-use.

    We have created this API for:

    * citizens interested in the activities of the state;
    * companies that build innovative products and services based on data;
    * NGOs using data in their daily work;
    * scientists carrying out research;
    * officials preparing reports and analyses.

    An up-to-date list of data providers is available [here](https://www.dane.gov.pl/institution).

    ## Contact

    All questions concerning the functioning of the API should be sent to: <kontakt@dane.gov.pl>.

    If you have created an application that uses public data available on the API,
    feel free to share it with us. We will publicise it on our [portal](https://www.dane.gov.pl).
    Contact us if you haven't found the data you need.
    Describe in detail the type of data you are looking for.
    We will analyse the possibility of making them available by providers.


    ## Information concerning GDPR
    1. The data controller can be contacted by post, sending correspondence
    to the address of the Administrator's office: ul. Królewska 27, 00-060 Warsaw or,
    via ePUAP, the address of which is available
    at https://www.gov.pl/web/cyfryzacja/dane-kontaktowe - the link will open in a new window,
    or by sending a letter to the address of the controller’s registered office.
    2. The controller has appointed a Data Protection Officer who can be contacted
    by e-mail at <iod.mc@cyfra.gov.pl>. The Data Protection Officer may be contacted on
    all matters concerning the processing of personal data and the exercise
    of data processing rights.
    3. Your personal data will be processed in order to operate the data.gov.pl website.
    The legal basis for the processing of your data is the necessity to fulfil
    the legal obligations of the controller under the provisions of the
    Act of 6 September 2001 on Access to Public Information.
    4. Your data will be kept for the period of time necessary for carrying out the goals.
    5. The provision of your personal data is necessary in order to operate
    the dane.gov.pl website. The provision of personal data is mandatory, in line
    with the legal basis mentioned above.
    6. The processing of your data may be restricted, except for valid considerations
    of public interest of the Republic of Poland or the European Union.
    7. You have the right to access and rectify your data. The right of rectification
    shall be exercised in accordance with relevant procedures in Poland.
    8. You have the right to lodge a complaint with the data protection supervisory
    authority of the Member State of your residence, place of work or place of the
    alleged breach.

    ####President of the Office for the Protection of Personal Data (PUODO)
    tel.: 22 531 03 00 or 606 950 000

    addr.: ul. Stawki 2, 00-193 Warsaw, Poland

    ## Legal basis

    The [DANE.GOV.PL API](https://api.dane.gov.pl) pursues the objective of the Central Public Data Repository,
    as described in the Act on Access to Public Information (Dz. U. [Journal of Laws] no. 112,
    item. 1198 as amended) as one of the modes of accessing and reusing public information.

    The following regulations were issued on the basis of the Act:

    * [Regulation of the Council of Ministers regarding
    the Central Public Information Repository](http://www.dziennikustaw.gov.pl/DU/2014/361/1)
    * [Regulation of the Minister of Digitalization of August 23,
    2018 regarding the information resource intended to be made
    available in the Central Public Information Repository](http://dziennikustaw.gov.pl/DU/2018/1790/1)
    * [Regulation of the Minister of Administration and Digitisation
    regarding the information resource to be made available in
    the Central Public Information Repository](http://www.dziennikustaw.gov.pl/DU/2014/491/1)
    * [Regulation of the Minister of Administration and Digitisation
    of the 5th of May 2015 amending the regulation
    regarding the information resource to be made available in
    the Central Public Information Repository](http://www.dziennikustaw.gov.pl/DU/2015/803/1)

    ## About the API
    #### Response Content-Type

    All API responses are in [JSON:API](https://jsonapi.org/) format.

    #### Versioning

    You can switch between API versions using the `X-API-VERSION` header in the request.
    If the `X-API-VERSION' header is not set, the latest released API version is used.

    Example:

            X-API-VERSION: 1.3

    It is also possible to change the API version by providing the API version in the path
    `https://dane.gov.pl/<api_ver>/<rest of the path>`.

    If the API version is not in the path, the answer in the latest version of the API will be returned


    Example - API 1.0:

            https://dane.gov.pl/1.0/datasets

    Example - API 1.4:

            https://dane.gov.pl/1.4/datasets

    Example - without a specify of API version:

            https://dane.gov.pl/datasets

    Attention! The api version indicated in the path has priority over the version indicated in the header


    ##### Available API versions:

    * 1.0 (release date: 14.09.2018)
    * 1.4 (release date: 17.01.2019)

    #### Translations

    By default, all API messages are translated into Polish. You can change this by setting
    the `Accept-Language` header, for example

            Accept-Language: en

    Note, than currently two languages are supported:

    * en
    * pl (default, as fallback)

    #### Errors

    The API uses standard HTTP status codes to indicate the success
    or failure of the API call. The body of the response will be JSON in
    the following format:

           {
              "errors": {
                "title": {
                  "xyz": [
                    "Unknown field."
                  ]
                }
              },
              "description": "Field value error",
              "code": "entity_error",
              "title": "422 Unprocessable Entity"
            }

    #### Basic data structures

    The API provides endpoints for the following data structures:

    * **resource** - contains information and "metadata" about the data published
    by the provider,
    * **dataset** - a package of resources which is owned by the institution
    publishing the data,
    * **institution** - the organisation, institution or company that publishes the data.

    """
    version = version or str(max(DOC_VERSIONS))
    if version not in DOC_VERSIONS:
        raise Exception("Unsupported API version")

    description = markdown2.markdown(markdown2._dedent(get_spec.__doc__))
    return APISpec(
        title="DANE.GOV.PL API",
        version=version,
        openapi_version="3.0.0",
        plugins=[MCODPlugin(version)],
        info={
            "description": description,
        },
    )
