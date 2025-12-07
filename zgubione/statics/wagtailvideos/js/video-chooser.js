function createVideoChooser(id) {
    var chooserElement = $('#' + id + '-chooser');
    var previewVideo = chooserElement.find('.preview-image img');
    var input = $('#' + id);
    var editLink = chooserElement.find('.edit-link');
     console.log("IN VIDEO CHOOSER");
     document.addEventListener('DOMContentLoaded', event => {
        var input = $('#' + id);
        let input_val = input.val();
        console.log("INPUT VAL:",input_val);
        if(input_val != ''){
            let call_url = window.chooserUrls.videoChooser + input.val() + '/';
            console.log("CALL URL", call_url);
            $.ajax(call_url).done(function(data) {
                let videoData = data.result
                console.log("videoData:", videoData);
                input.val(videoData.id);
                    previewVideo.attr({
                        src: videoData.preview.url,
                        alt: videoData.title
                    });
                    chooserElement.removeClass('blank');
                    editLink.attr('href', videoData.edit_link);
            });
        }
    })

    $('.action-choose', chooserElement).click(function() {
        ModalWorkflow({
            url: window.chooserUrls.videoChooser,
            onload: VIDEO_CHOOSER_MODAL_ONLOAD_HANDLERS,
            responses: {
                videoChosen: function(videoData) {
                    input.val(videoData.id);
                    previewVideo.attr({
                        src: videoData.preview.url,
                        alt: videoData.title
                    });
                    chooserElement.removeClass('blank');
                    editLink.attr('href', videoData.edit_link);
                }
            }
        });
    });

    $('.action-clear', chooserElement).click(function() {
        input.val('');
        chooserElement.addClass('blank');
    });
}
