$(document).ready(function(){ 
    //$('#startup_scripts_button').button();
    //$("#startup_scripts_button").click(function() { $('#further-instructions').show(); });
    
    $('#check_files_button').button().click(function() {
      $(this).button('disable');
      $('#qc-status').empty();
      $('#qc-status').append('Verifying data and files... <img src="images/busy.gif" />');
      $('#check_files_button').button("option","disabled",true);
      $.post("creds_and_qc.cgi", { all_objects: JSON.stringify(get_all_data()) },
          function(response){
              qc_handle_response(response);
          }
      );
    });
    $('#start_button').button({disabled:true});
    $('#start_button').click(function() {
        $.post("run_mapping.cgi", { all_objects: JSON.stringify(get_all_data()) },
            function(response){
                mapping_handle_response(response);
            }
        );
    });
    $("#amazon-request-types").buttonset();
    $("#advanced_settings").accordion({
            collapsible: true,
            active: false,
            alwaysOpen: false,
            autoHeight: false,
            clearStyle: true
    });
    $('select').selectmenu({
        width: 200
    });
    $('#alignment-pipeline').selectmenu({
        select: function(event, options) {
            $('#map-advanced-links > div').hide();
            $('#' + options.value + '-advanced-link').show();
        }
    });
    $('#calling-pipeline').selectmenu({
        select: function(event, options) {
            $('#call-advanced-links > div').hide();
            $('#' + options.value + '-advanced-link').show();
        }
    });
    $('#own-url-data').attr("href", 'sftp://root@' + document.domain + ':/mnt/stormseq_data');
    $('#own-url-home').attr("href", 'sftp://root@' + document.domain + ':/root/');
    refresh_spot_prices(); 
});

function get_values_from_textarea(pipeline) {
    output_obj = {}
    $.each($('#' + pipeline + '-advanced > textarea'), function(i, v) {
        output_obj[v.id] = $(v).innerText;
    });
    return(output_obj);
}

function get_values_from_checkboxes(pipeline) {
    output_obj = {}
    $.each($('#' + pipeline + '-advanced > input'), function(i, v) {
        output_obj[v.id] = v.checked;
    });
    return(output_obj);
}

function get_all_data() {
    var output = {
        aws_account_number: $('#aws-account-number').val(),
        access_key_id: $('#access-key-id').val(),
        secret_access_key: $('#secret-access-key').val(),
        genome_version: $('#genome-version').val(),
        dbsnp_version: $('#dbsnp-version').val(),
        alignment_pipeline: $('#alignment-pipeline').val(),
        calling_pipeline: $('#calling-pipeline').val()                
    };
    $.extend(output, get_values_from_textarea($('#alignment-pipeline').val()));
    $.extend(output, get_values_from_checkboxes('gatk-clean'));
    $.extend(output, get_values_from_checkboxes($('#calling-pipeline').val()));
    $.extend(output, get_values_from_textarea($('#calling-pipeline').val()));
    output['request_type'] = $('#amazon-request-types input:checked').val();
    $.extend(output, get_values_from_textarea('amazon'));
    return(output);
}

function qc_handle_response(response) {
    $('#qc-status').empty();
    if (response.search('qc-fail') > -1) {
        $('#qc-status').append('QC has failed. Check your input files.<br/><br/>Error:<br/>' + response);
        $('#check_files_button').button("option","disabled",false);
    } else {
        $('#qc-status').append('Passed QC!');
        $('#check_files_button').button("option","disabled",false);
        if (response == 'cert-fail') {
            $('#qc-status').append('<br/>Amazon PEM files are gone. Check cert*pem and pk*pem in /root/ directory.');
            $('#check_files_button').button("option","disabled",false);
        } else {
            if (response == 'auth-fail') {
                $('#qc-status').append('<br/>Could not authenticate Amazon account from Account Number, Access Key ID, or Secret Access Key. Check these inputs.');
                $('#check_files_button').button("option","disabled",false);
            } else if (response == 'success') {
                $('#qc-status').append('<br/>Your pipeline is ready! Click GO to begin!');
                $('#start_button').button("option","disabled",false);
            } else {
                $('#qc-status').append('<br/>Something new went wrong. Please <a href="mailto:help@stormseq.org">email</a> us with these details:<br/><br/>' + response);
                $('#check_files_button').button("option","disabled",false);
            }
        }
    }
}

function mapping_handle_response(response) {
    console.log('mapping: ' + response);
}

function refresh_spot_prices() {
    $('#large-current-price').html('Loading... <img src="images/busy.gif" />');
    $('#hi-mem-current-price').html('Loading... <img src="images/busy.gif" />');
    
    $.post("get_current_prices.cgi", { all_objects: JSON.stringify(get_all_data()) },
        function(response){
            prices = response.split(',');
            $('#large-current-price').text(prices[0]);
            $('#hi-mem-current-price').text(prices[1]);
        }
    );
}