$(document).on('click', '.panel-heading span.clickable', function (e) {
    if (!$(this).hasClass('panel-collapsed')) {
        $(this).parents('.panel').find('.panel-body').slideUp();
        $(this).addClass('panel-collapsed');
        $(this).find('i').removeClass('glyphicon-chevron-up').addClass('glyphicon-chevron-down');
    } else {
        $(this).parents('.panel').find('.panel-body').slideDown();
        $(this).removeClass('panel-collapsed');
        $(this).find('i').removeClass('glyphicon-chevron-down').addClass('glyphicon-chevron-up');
    }
});
$(document).on('click', '#schemaAll', function (e) {
    if ($(this).is(':checked')) {
        $('.yang-schema-select').prop('checked', true);
    } else {
        $('.yang-schema-select').prop('checked', false);
    }
});
$(document).on('click', '.yang-schema-select', function (e) {
    if (!$(this).is(':checked')) {
        $('#schemaAll').prop('checked', false);
    } else {
        var allChecked = true;
        $('.yang-schema-select').each(function (i, e) {
            if (!$(this).is(':checked')) {
                allChecked = false;
                return;
            }
        });
        if (allChecked) {
            $('#schemaAll').prop('checked', true);
        }
    }
});
$(document).on('click', '#fieldsAll', function (e) {
    if ($(this).is(':checked')) {
        $('.yang-fields-select').prop('checked', true);
    } else {
        $('.yang-fields-select').prop('checked', false);
    }
});
$(document).on('click', '.yang-fields-select', function (e) {
    if (!$(this).is(':checked')) {
        $('#fieldsAll').prop('checked', false);
    } else {
        var allChecked = true;
        $('.yang-fields-select').each(function (i, e) {
            if (!$(this).is(':checked')) {
                allChecked = false;
                return;
            }
        });
        if (allChecked) {
            $('#fieldsAll').prop('checked', true);
        }
    }
});
$(document).on('click', '#regexp', function (e) {
    if ($(this).is(':checked')) {
        $('#search_string').prop('placeholder', 'Search Pattern');
    } else {
        $('#search_string').prop('placeholder', 'Search String');
    }
});
$(document).on('click', '#headersAll', function (e) {
    if ($(this).is(':checked')) {
        $('.yang-headers-select').prop('checked', true);
    } else {
        $('.yang-headers-select').prop('checked', false);
    }
});
$(document).on('click', '.yang-headers-select', function (e) {
    if (!$(this).is(':checked')) {
        $('#headersAll').prop('checked', false);
    } else {
        var allChecked = true;
        $('.yang-headers-select').each(function (i, e) {
            if (!$(this).is(':checked')) {
                allChecked = false;
                return;
            }
        });
        if (allChecked) {
            $('#headersAll').prop('checked', true);
        }
    }
});
function verify() {
    if (!$('#search_string').val().trim()) {
        alert('Please specify search terms.');
        return false;
    }
    return true;
}
