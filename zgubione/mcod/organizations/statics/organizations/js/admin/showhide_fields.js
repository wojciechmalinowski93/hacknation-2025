// (function ($) {
//    $(function () {
//       var $select = $('select[id*="external"]'),
//         $file = $('[type=file][id*="url"]').hide(),
//         $input = $('[type=url][id*="url"]').hide(),
//         externalHandler = function (number) {
//            if(number && number == 2) {
//                $input.slideDown();
//                $file.slideUp();
//            }
//
//            if(number && number == 3) {
//                $input.slideUp();
//                 $file.slideDown();
//            }
//        };
//
//        $select.on('change', function() {
//            externalHandler( $(this).val() );
//        });
//
//        externalHandler( $select.val() );
//    });
// })(django.jQuery);
