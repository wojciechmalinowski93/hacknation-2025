var button = '<button type="button" id="add_customfield" class="add-related customfields"><img src="/static/admin/img/icon-addlink.svg" alt="Dodaj"></button>';
var pair = '<br><input type="text" name="json_key[customfields]" value="key" class="large" "=""><input type="text" name="json_value[customfields]" value="value" size="35">';


$(document).ready(function () {

    $('.customfields').last().after(button)

    $('#add_customfield').click(function () {
        $(this).before(pair);
    })

})


// (function ($) {
//     var button = '<br><a class="add-related" id="add_customfield" href="#add_customfield"><img src="/static/admin/img/icon-addlink.svg" alt="Dodaj"></a>';
//     var pair = '<input type="text" name="json_key[customfields]" value="key" class="large" "=""><input type="text" name="json_value[customfields]" value="value" size="35"><br>';
//
//     $('.customfields').last().after(button)
//
//     $('#add_customfield').click(function () {
//         $(this).before(pair);
//     })
//
// }(django.jQuery));
