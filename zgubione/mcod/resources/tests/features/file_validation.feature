@otd_1152
Feature: File validation

  Scenario Outline: Validation of various file types
    Given I have file <file_type>
    Then file is validated and result is <file_format>
    Examples:
      | file_type                        | file_format |
      | docx                             | docx        |
      | geojson                          | geojson     |
      | geojson without extension        | geojson     |
      | json with geojson content        | geojson     |
      | jsonld                           | jsonld      |
      | jsonstat                         | jsonstat    |
      | ods                              | ods         |
      | xlsx                             | xlsx        |
      | zip with one csv                 | zip         |
      | tar.gz with one csv              | gz          |
      | empty_file.7z                    | 7z          |
      | empty_file.rar                   | rar         |
      | empty_docx_packed.rar            | rar         |
      | empty_file.tar.gz                | gz          |
      | empty_file.tar.bz2               | bz2         |
      | shapefile arch                   | shp         |
      | gpx                              | gpx         |
      | grib                             | grib        |
      | hdf_netcdf                       | nc          |
      | binary_netcdf                    | nc          |
      | cp1251.dbf                       | dbf         |
      | dbase_03.dbf                     | dbf         |
      | dbase_30.dbf                     | dbf         |
      | dbase_31.dbf                     | dbf         |
      | dbase_83.dbf                     | dbf         |
      | dbase_83_missing_memo.dbf        | dbf         |
      | dbase_8b.dbf                     | dbf         |
      | dbase_f5.dbf                     | dbf         |
      | n3                               | n3          |
      | n_triples                        | n3          |
      | n_quads                          | nq          |
      | rdf                              | rdf         |
      | turtle                           | n3         |
      | trig                             | trig        |
      | trix                             | trix        |
      | regular.zip                      | zip         |
      | regular.7z                       | 7z          |
      | regular.rar                      | rar         |
      | zip with many files              | zip         |
      | zip with many files no extension | zip         |

  Scenario Outline: Validation of password protected archives
    Given I have file <file_type>
    Then file is validated and PasswordProtectedArchiveError is raised
    Examples:
      | file_type                         |
      | encrypted_content.zip             |
      | encrypted_content.7z              |
      | encrypted_content_and_headers.7z  |
      | encrypted_content.rar             |
      | encrypted_content_and_headers.rar |

  Scenario Outline: Validation of rar with many files
    Given I have file <file_type>
    Then file is validated and UnsupportedArchiveError is raised
    Examples:
      | file_type           |
      | rar with many files |
      | zip with many files |

  Scenario Outline: Validation of various file mimetypes
    Given I have file <file_type>
    Then file is validated and result mimetype is <mimetypes>
    Examples:
      | file_type     | mimetypes                                    |
      | grib          | ["application/x-grib"]                       |
      | hdf_netcdf    | ["application/netcdf", "application/x-hdf5"] |
      | binary_netcdf | ["application/netcdf"]                       |

  Scenario Outline: Validation of various extracted file types
    Given I have file <file_type>
    Then extracted file is validated and result is <file_format>
    Examples:
      | file_type             | file_format |
      | regular.zip           | csv         |
      | regular.7z            | csv         |
      | regular.rar           | csv         |
      | zip with one csv      | csv         |
      | tar.gz with one csv   | csv         |
      | empty_file.7z         | csv         |
      | empty_file.rar        | csv         |
      | empty_docx_packed.rar | docx        |
      | empty_file.tar.gz     | csv         |
      | empty_file.tar.bz2    | csv         |
      | json_in_zip.zip       | geojson     |
