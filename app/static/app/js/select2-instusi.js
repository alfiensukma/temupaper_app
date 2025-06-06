// select2-init.js
$(document).ready(function() {
    $('.institution-select').select2({
        placeholder: "Pilih institusi Anda",
        allowClear: true,
        width: '100%',
        dropdownParent: $('.institution-select').parent(),
        selectionCssClass: 'custom-select2-selection',
        dropdownCssClass: 'custom-select2-dropdown'
    }).on('select2:open', function() {
        // Focus the search field when opened
        setTimeout(function() {
            $('.select2-search__field').focus();
        }, 100);
    });
    
    // Fix for mobile devices
    $(document).on('select2:open', () => {
        document.querySelector('.select2-search__field').focus();
    });
});