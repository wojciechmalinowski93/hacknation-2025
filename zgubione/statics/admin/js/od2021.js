// HOME - quick access menu
$('.table-overview').each(function () {
	var $this = $(this);
	var $sectionBody = $this.find('tbody');
	$this.find('a.section').on('click', function (event) {
		event.preventDefault();
		$sectionBody.toggle();
	});
});
