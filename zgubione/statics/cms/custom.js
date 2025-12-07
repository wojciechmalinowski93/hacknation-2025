$(function () {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    let dialogInitialized = false;

    function initDialog() {
        $("<div class='copy_pl_to_en_overlay'></div>").appendTo('body');
        $(`
            <div class='copy_pl_to_en_dialog'>
                <p>Przekopiowanie treści z wersji PL powoduje nadpisanie obecnej zawartości zakładki TREŚĆ (EN).</p>
                <p>Czy mimo to kontynuować?</p>
                <div>
                    <span class="dialog_reject">NIE</span>
                    <span class="dialog_accept">TAK</span>
                </div>
            </div>
        `).appendTo('body');

        $("span.dialog_reject").on('click', function () {
            closeDialog();
        });

        $("span.dialog_accept").on('click', function () {
            closeDialog();
            const regex = /admin\/pages\/(\d+)\/edit/;
            const page_id = window.location.pathname.match(regex)[1];
            const url = `/copy_pl_to_en/${page_id}/`;
            $.ajax({
                url: url,
                type: 'post',
                headers: {'X-CSRFToken': csrftoken},
                success: function (data) {
                    if (data.success) {
                        window.location.hash = section_en.id;
                        window.location.reload(true);
                    }
                }
            });
        });
    }

    function openDialog() {
        if (!dialogInitialized) {
            initDialog();
            dialogInitialized = true;
        }
        $(".copy_pl_to_en_overlay").show();
        $(".copy_pl_to_en_dialog").show();
    }

    function closeDialog() {
        $(".copy_pl_to_en_overlay").hide();
        $(".copy_pl_to_en_dialog").hide();
    }

    const section_en = document.getElementById('tab-tresc-en') || document.getElementById('tab-formularz-en');
    if(section_en != null){
        const wrapper = document.createElement('div');
        wrapper.className = "copy_pl_to_en";

        const button = document.createElement('span');
        button.innerText = "Przekopiuj treść z wersji PL";
        button.onclick = function () {
            openDialog();
        };
        wrapper.appendChild(button);
        section_en.prepend(wrapper);
    }
});
