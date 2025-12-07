@elasticsearch
Feature: Subscriptions API
  Scenario: Listing for anonymous user
    Given admin has subscription with id 2100 of dataset with id 1200 as dataset-1200

    When api request path is /auth/subscriptions
    And send api request and fetch the response
    Then api's response status code is 401
    And size of api's response body field /errors is 1
    And api's response body field /errors/[0]/code is 401_unauthorized


  Scenario: Listing for logged in user
    Given logged active user
    And subscription with id 2101 of dataset with id 1201 as dataset-1201
    And subscription with id 2102 of removed dataset with id 1202 as removed-dataset-1202
    And subscription with id 2103 of draft dataset with id 1203 as draft-dataset-1203
    And admin has subscription with id 2104 of dataset with id 1204 as dataset-1204

    When api request path is /auth/subscriptions
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 1
    And api's response body field /data/*/type is subscription
    And api's response body has field /data/*/attributes/title
    And api's response body has field /data/*/attributes/created
    And api's response body has field /data/*/attributes/modified
    And api's response body has field /data/*/attributes/customfields
    And api's response body has field /data/*/relationships/subscribed_object
    And api's response body has field /data/*/relationships/notifications
    And api's response body field /data/[0]/attributes/title is dataset-1201
    And api's response body field /data/[0]/relationships/subscribed_object/data/type is dataset


  Scenario: Listing filtering for logged in user
    Given logged active user
    And 3 subscriptions of random dataset
    And query subscription with id 2105 for url /search?model[terms]=dataset as subscription_name

    When api request path is /auth/subscriptions
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 4
    And api's response body field /data/*/attributes/title contains subscription_name

    And api request path is /auth/subscriptions?object_name=dataset
    And send api request and fetch the response
    And api's response body field /meta/count is 3
    And api's response body field /data/*/relationships/subscribed_object/data/type is dataset

    And api request path is /auth/subscriptions?object_name=query
    And send api request and fetch the response
    And api's response body field /meta/count is 1
    And api's response body field /data/*/relationships/subscribed_object/data/type is query


  Scenario: Listing filtering with invalid id for logged in user
    Given logged active user
    And subscription with id 2106 of dataset with id 1205 as dataset-1205

    When api request path is /auth/subscriptions?object_name=invalid_object
    And send api request and fetch the response
    Then api's response status code is 422


  Scenario: Listing filtering with object_name and object_id for logged in user
    Given logged active user
    And subscription with id 2107 of dataset with id 1205 as dataset-1205
    And subscription with id 2108 of dataset with id 1206 as dataset-1206
    And query subscription with id 2109 for url /search?model[terms]=dataset as query-2109
    And query subscription with id 2110 for url /search?model[terms]=resource as query-2110

    When api request path is /auth/subscriptions
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 4

    And api request path is /auth/subscriptions?object_name=dataset&object_id=1205
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 1
    And api's response body field /data/*/relationships/subscribed_object/data/type is dataset

    And api request path is /auth/subscriptions?object_name=query&object_id=%2Fsearch%3Fmodel[terms]%3Ddataset
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 1
    And api's response body field /data/*/relationships/subscribed_object/data/type is query


  Scenario: Listing filtering with object_id for logged in user
    Given logged active user
    And subscription with id 2111 of dataset with id 1206 as dataset-1206
    And subscription with id 2112 of dataset with id 1207 as dataset-1207
    And subscription with id 2113 of institution with id 1206 as institution-1206

    When api request path is /auth/subscriptions?object_id=1206
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 2
    And api's response body field /data/[0]/attributes/title is institution-1206
    And api's response body field /data/[1]/attributes/title is dataset-1206
    And api's response body field /data/[0]/relationships/subscribed_object/data/type is institution
    And api's response body field /data/[1]/relationships/subscribed_object/data/type is dataset


  Scenario: Listing filtering with invalid object_id for logged in user
    Given logged active user
    And subscription with id 2114 of dataset with id 1208 as dataset-1208

    When api request path is /auth/subscriptions?object_id=9999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 0

    And api request path is /auth/subscriptions?object_name=dataset&object_id=9999
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 0


  Scenario: Subscription with id 2114
    Given logged active user
    And subscription with id 2114 of dataset with id 1209 as dataset-1209

    When api request path is /auth/subscriptions/2114
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/type is subscription
    And api's response body field /data/id is 2114
    And api's response body field /data/attributes/title is dataset-1209
    And api's response body has field /data/attributes/created
    And api's response body has field /data/attributes/modified
    And api's response body has field /data/attributes/customfields
    And api's response body has field /data/relationships/subscribed_object
    And size of api's response body field /included is 1
    And api's response body field /data/relationships/subscribed_object/data/type is dataset


  Scenario: Dataset subscription
    Given logged active user
    And dataset with id 1210

    When api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is dataset
    And api request body field /data/attributes/object_ident is 1210
    And api request body field /data/attributes/name is my-subscription
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field /data/attributes/title is my-subscription
    And api's response body field /data/relationships/subscribed_object/data/id is 1210
    And api's response body field /data/attributes/customfields/something is nothing
    And api's response body field /data/type is subscription
    And api's response body has field /data/attributes/created
    And api's response body has field /data/attributes/modified
    And api's response body has field /data/attributes/customfields

    And api request method is GET
    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 1
    And api's response body field /data/[0]/relationships/subscribed_object/data/id is 1210
    And api's response body field /data/[0]/attributes/customfields/something is nothing
    And api's response body field /data/[0]/attributes/title is my-subscription
    And size of api's response body field /included is 1
    And api's response body field /data/[0]/type is subscription
    And api's response body has field /data/[0]/attributes/created
    And api's response body has field /data/[0]/attributes/modified
    And api's response body has field /data/[0]/attributes/customfields


  Scenario: Subscribe dataset as not logged in user
    Given dataset with id 1211

    When api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is dataset
    And api request body field /data/attributes/object_ident is 1211
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 401


  Scenario: Subscription with id 2115 for anonymous user
    Given admin has subscription with id 2115 of dataset with id 1212 as dataset-1212

    When api request path is /auth/subscriptions/2115
    And send api request and fetch the response
    Then api's response status code is 401
    And api's response body field /errors/[0]/code is 401_unauthorized


  Scenario: Admin's subscription with id not accessable for other user
    Given logged active user
    And admin has subscription with id 2116 of dataset with id 1213 as dataset-1213

    When api request path is /auth/subscriptions/2116
    And send api request and fetch the response
    Then api's response status code is 404
    And api's response body field /errors/[0]/code is 404_not_found


  Scenario: Change subscription for dataset
    Given logged active user
    And subscription with id 2117 of dataset with id 1214 as dataset-1214

    When api request method is PATCH
    And api request path is /auth/subscriptions/2117
    And api request body field /data/type is subscription
    And api request body field /data/id is 2117
    And api request body field /data/attributes/name is my-subscription
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/attributes/title is my-subscription
    And api's response body field /data/attributes/customfields/something is nothing
    And size of api's response body field /included is 1
    And api's response body field /included/[0]/type is dataset

    And api request method is GET
    And api request path is /auth/subscriptions/
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/[0]/attributes/title is my-subscription
    And api's response body field /data/[0]/attributes/customfields/something is nothing
    And size of api's response body field /included is 1
    And api's response body field /included/[0]/type is dataset


  Scenario: Delete subscription for dataset
    Given logged active user
    And subscription with id 2118 of dataset with id 1215 as dataset-1215
    And subscription with id 2119 of dataset with id 1216 as dataset-1216

    When api request method is DELETE
    And api request path is /auth/subscriptions/2118
    And send api request and fetch the response
    Then api's response status code is 204

    And api request method is GET
    And send api request and fetch the response
    And api's response status code is 404

    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response body field /meta/count is 1
    And api's response body field /data/[0]/attributes/title is dataset-1216


  Scenario: User can create only one subscription of an dataset
    Given logged active user
    And subscription with id 2120 of dataset with id 1217 as dataset-1217

    When api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is dataset
    And api request body field /data/attributes/object_ident is 1217
    And api request body field /data/attributes/name is new-name
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 403

    And api request method is GET
    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 1
    And api's response body field /data/[0]/attributes/title is dataset-1217
    And api's response body field /data/[0]/attributes/customfields is None


  Scenario: Subscription info available on objects listing for logged in user
    Given logged active user
    And admin has subscription with id 2121 of dataset with id 1218 as dataset-1218
    And subscription with id 2122 of dataset with id 1219 as dataset-1219
    And dataset with id 1220

    When api request path is /datasets
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 3
    And api's response body has no field /data/[0]/relationships/subscription
    And api's response body field /data/[1]/relationships/subscription/data/type is subscription
    And api's response body has no field /data/[2]/relationships/subscription


  Scenario: Subscription info available in object with id 2123 for logged in user
    Given logged active user
    And subscription with id 2123 of dataset with id 1221 as dataset-1221

    When api request path is /datasets
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/[0]/relationships/subscription/data/type is subscription
    And api's response body field /data/[0]/relationships/subscription/data/id is 2123


  Scenario: Subscription info not available in object with id 2124 for logged in user new
    Given logged active user
    And admin has subscription with id 2124 of dataset with id 1222 as dataset-1222

    When api request path is /datasets
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 1
    And api's response body has no field /data/[0]/relationships/subscription


  Scenario: Subscription info not available in object with id 2125 for anonymous user
    Given admin has subscription with id 2125 of dataset with id 1223 as dataset-1223

    When api request path is /datasets
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 1
    And api's response body has no field /data/[0]/relationships/subscription


  Scenario: Deleted subscription info is not available on datasets listing
    Given logged active user
    And subscription with id 2126 of dataset with id 1224 as dataset-1224
    And subscription with id 2127 of dataset with id 1225 as dataset-1225

    When api request path is /datasets
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 2
    And api's response body has field /data/*/relationships/subscription

    And api request method is DELETE
    And api request path is /auth/subscriptions/2127
    And send api request and fetch the response
    And api's response status code is 204

    And api request method is GET
    And api request path is /datasets
    And send api request and fetch the response
    And api's response body field /meta/count is 2
    And api's response status code is 200
    And api's response body has field /data/0/relationships/subscription
    And api's response body has no field /data/1/relationships/subscription


  Scenario: Subscribe query as logged in user
    Given logged active user

    When api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is query
    And api request body field /data/attributes/object_ident is http://api.test.mcod/datasets
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field /data/attributes/title is query-http://api.test.mcod/datasets
    And api's response body field /data/relationships/subscribed_object/data/type is query
    And api's response body field /data/relationships/subscribed_object/data/id is http://api.test.mcod/datasets
    And api's response body field /data/type is subscription
    And api's response body field /data/attributes/customfields/something is nothing
    And api's response body has field /data/attributes/created
    And api's response body has field /data/attributes/modified
    And api's response body has field /data/attributes/customfields

    And api request method is GET
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 1
    And api's response body field /data/[0]/attributes/title is query-http://api.test.mcod/datasets
    And api's response body field /data/[0]/relationships/subscribed_object/data/type is query
    And api's response body field /data/[0]/relationships/subscribed_object/data/id is http://api.test.mcod/datasets
    And api's response body field /data/*/type is subscription
    And api's response body field /data/[0]/attributes/customfields/something is nothing
    And api's response body has field /data/*/attributes/created
    And api's response body has field /data/*/attributes/modified
    And api's response body has field /data/*/attributes/customfields


  Scenario: Subscribe query with wrong url as logged in user
    Given logged active user

    When api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is query
    And api request body field /data/attributes/object_ident is https://www.google.com/search?q=dane
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field /errors/[0]/code is 422_unprocessable_entity
    And size of api's response body field errors is 1


  Scenario: Subscribe query with wrong url as anonymous user
    When api request method is POST

    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is query
    And api request body field /data/attributes/object_ident is http://api.test.mcod/datasets
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 401
    And api's response body field /errors/[0]/code is 401_unauthorized
    And size of api's response body field errors is 1


  Scenario: Subscribe invalid object as logged in user
    Given logged active user

    When api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is invalid_object
    And api request body field /data/attributes/object_ident is 123
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field /errors/[0]/code is 422_unprocessable_entity
    And size of api's response body field errors is 1


  Scenario: Subscribe query twice as logged in user
    Given logged active user
    And query subscription with id 2128 for url http://api.test.mcod/datasets?a=1&b=2&c=3 as first-query

    When api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is query
    And api request body field /data/attributes/object_ident is http://api.test.mcod/datasets?b=2&c=3&a=1
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field /errors/[0]/code is 403_forbidden
    And size of api's response body field errors is 1


  Scenario: Delete query subscription as logged in user
    Given logged active user
    And query subscription with id 2129 for url http://api.test.mcod/datasets?a=1&b=2&c=3 as first-query
    And subscription with id 2130 of dataset with id 1226 as dataset-1226

    When api request method is DELETE
    And api request path is /auth/subscriptions/2129
    And send api request and fetch the response
    Then api's response status code is 204

    And api request method is GET
    And send api request and fetch the response
    And api's response status code is 404
    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response body field /meta/count is 1
    And api's response body field /data/[0]/attributes/title is dataset-1226


  Scenario: Subscription with duplicated name as logged in user
    Given logged active user
    And query subscription with id 2131 for url http://api.test.mcod/datasets?c=123 as test-query

    When api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is query
    And api request body field /data/attributes/name is test-query-1
    And api request body field /data/attributes/object_ident is http://api.test.mcod/datasets?a=123
    And send api request and fetch the response
    Then api's response status code is 201

    And api request path is /auth/subscriptions
    And api request body field /data/type is subscription
    And api request body field /data/attributes/object_name is query
    And api request body field /data/attributes/name is test-query
    And api request body field /data/attributes/object_ident is http://api.test.mcod/datasets?d=123
    And send api request and fetch the response
    And api's response status code is 403
    And api's response body field /errors/[0]/code is 403_forbidden
    And size of api's response body field errors is 1

    And api request method is PATCH
    And api request body field /data is of type dict
    And api request path is /auth/subscriptions/2131
    And api request body field /data/type is subscription
    And api request body field /data/id is 2131
    And api request body field /data/attributes/name is test-query-1
    And send api request and fetch the response
    And api's response status code is 403
    And api's response body field /errors/[0]/code is 403_forbidden
    And size of api's response body field errors is 1


  Scenario: Update query subscription as logged in user
    Given logged active user
    And query subscription with id 2132 for url http://api.test.mcod/datasets?a=1&b=2&c=3 as first-query
    And subscription with id 2133 of dataset with id 1227 as dataset-1227

    When api request method is PATCH
    And api request path is /auth/subscriptions/2132
    And api request body field /data/type is subscription
    And api request body field /data/id is 2132
    And api request body field /data/attributes/name is changed-name
    And api request body field /data/attributes/customfields/something is nothing
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/attributes/title is changed-name
    And api's response body field /data/attributes/customfields/something is nothing

    And api request method is GET
    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 2
    And api's response body field /data/[1]/attributes/title is changed-name
    And api's response body field /data/[1]/relationships/subscribed_object/data/type is query
    And api's response body field /data/[1]/relationships/subscribed_object/data/id is http://api.test.mcod/datasets?a=1&b=2&c=3
    And api's response body field /data/[1]/attributes/customfields/something is nothing
    And api's response body field /data/*/type is subscription
    And api's response body has field /data/*/attributes/created
    And api's response body has field /data/*/attributes/modified
    And api's response body has field /data/*/attributes/customfields


  Scenario: Subscribed query flag as logged in user
    Given logged active user
    And query subscription with id 2134 for url http://api.test.mcod/datasets?c=1&b=2 as datasets-listing-with-params
    And admin has query subscription with id 2135 for url http://api.test.mcod/datasets as datasets-listing-no-params

    When api request path is /datasets?b=2&c=1
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/subscription_url is http://api.test.mcod/auth/subscriptions/2134

    And api request path is /datasets
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body has no field subscribed_url


  Scenario: Subscribed query flag as admin user
    Given logged admin user
    And query subscription with id 2136 for url http://api.test.mcod/datasets?c=1&b=2 as datasets-listing-with-params
    And admin has query subscription with id 2137 for url http://api.test.mcod/datasets as datasets-listing-no-params

    When api request path is /datasets?b=2&c=1
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has no field subscribed_url

    And api request path is /datasets
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/subscription_url is http://api.test.mcod/auth/subscriptions/2137


  Scenario: Subscribed query flag as anonymous user
    Given dataset
    And admin has query subscription with id 2138 for url http://api.test.mcod/datasets as admin-datasets

    When api request path is /datasets
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has no field subscribed_url


  Scenario: Subscribed object has been changed to draft
    Given logged active user
    And subscription with id 2139 of dataset with id 1228 as dataset-1228
    And subscription with id 2140 of dataset with id 1229 as dataset-1229

    When api request path is /auth/subscriptions
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 2
    And api's response body field /data/[0]/attributes/title is dataset-1229

    # check that number of observed datasets on user's dashboard is the same.
    And api request path is /auth/user/dashboard
    And send api request and fetch the response
    And api's response body field /meta/aggregations/subscriptions/datasets is 2

    And api request path is /auth/subscriptions/2139
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /data/attributes/title is dataset-1228

    And set status to draft on dataset with id 1228

    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response body field /meta/count is 1

    # check that number of observed datasets on user's dashboard is the same.
    And api request path is /auth/user/dashboard
    And send api request and fetch the response
    And api's response body field /meta/aggregations/subscriptions/datasets is 1

    # check that notifications response status is ok.
    And api request path is /auth/notifications?object_name=dataset
    And send api request and fetch the response
    And api's response status code is 200

    And api request path is /auth/subscriptions/2139
    And send api request and fetch the response
    And api's response status code is 404

    And set status to published on dataset with id 1228

    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response body field /meta/count is 2

    # check that number of observed datasets on user's dashboard is the same.
    And api request path is /auth/user/dashboard
    And send api request and fetch the response
    And api's response body field /meta/aggregations/subscriptions/datasets is 2

    # check that notifications response status is ok.
    And api request path is /auth/notifications?object_name=dataset
    And send api request and fetch the response
    And api's response status code is 200

    And api request path is /auth/subscriptions/2139
    And send api request and fetch the response
    And api's response status code is 200

    And api request path is /auth/notifications?object_name=dataset
    And send api request and fetch the response
    And api's response status code is 200

  Scenario: Subscribed object has been removed
    Given logged active user
    And subscription with id 2141 of dataset with id 1230 as dataset-1230
    And subscription with id 2142 of dataset with id 1231 as dataset-1231

    When api request path is /auth/subscriptions
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 2
    And api's response body field /data/[1]/attributes/title is dataset-1230

    # check that number of observed datasets on user's dashboard is the same.
    And api request path is /auth/user/dashboard
    And send api request and fetch the response
    And api's response body field /meta/aggregations/subscriptions/datasets is 2

    And api request path is /auth/subscriptions/2141
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /data/attributes/title is dataset-1230

    And remove dataset with id 1230

    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response body field /meta/count is 1
    And api's response body field /data/[0]/attributes/title is dataset-1231

    # check that number of observed datasets on user's dashboard is the same.
    And api request path is /auth/user/dashboard
    And send api request and fetch the response
    And api's response body field /meta/aggregations/subscriptions/datasets is 1

    # check that notifications response status is ok.
    And api request path is /auth/notifications?object_name=dataset
    And send api request and fetch the response
    And api's response status code is 200

    And api request path is /auth/subscriptions/2141
    And send api request and fetch the response
    And api's response status code is 404

    And restore dataset with id 1230

    And api request path is /auth/subscriptions
    And send api request and fetch the response
    And api's response body field /meta/count is 2
    And api's response body field /data/[1]/attributes/title is dataset-1230

    # check that number of observed datasets on user's dashboard is the same.
    And api request path is /auth/user/dashboard
    And send api request and fetch the response
    And api's response body field /meta/aggregations/subscriptions/datasets is 2

    # check that notifications response status is ok.
    And api request path is /auth/notifications?object_name=dataset
    And send api request and fetch the response
    And api's response status code is 200

    And api request path is /auth/subscriptions/2141
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field /data/attributes/title is dataset-1230

    And api request path is /auth/notifications?object_name=dataset
    And send api request and fetch the response
    And api's response status code is 200
