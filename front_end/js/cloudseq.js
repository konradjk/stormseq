$(document).ready(function(){     
    speed = 500;
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
        $(this).button('disable');
        $('#run-status').empty();
        $('#run-status').append('Doing final checks and starting cluster... <img src="images/busy.gif" /><br/>');
        $('#run-status').append('(This may take several minutes.)');
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
    
    $('.qtip-link').qtip({
        content: {
            attr: 'qtip-content'
        },
        position: {
            my: 'top left',
            target: 'mouse',
            viewport: $(window), // Keep it on-screen at all times if possible
            adjust: {
                x: 10,  y: 10
            }
        },
        hide: {
            fixed: true // Helps to prevent the tooltip from hiding ocassionally when tracking!
        },
        style: 'ui-tooltip-shadow'
    });
    $('.autosave_restore').click();
    $('textarea').autosave({cookieExpiryLength: 30});
    $('.autosave_restore').click();
    progress_id = setInterval(update_charts, 300000);
    refresh_vis();
});

function refresh_vis() {
    $('#visualize-results').empty();
    $.post('visualize.cgi', { sample_name: JSON.stringify($('#sample_name').val()) }, function(response) {
        $('#visualize-results').append(response);
    });
}

function click_refresh_progress() {
    $('#progress-chart').empty();
    $('#progress-chart-2').empty();
    
    $('#progress-chart').append('Checking progress... <img src="images/busy.gif" />');
    $.post('check_progress.cgi', { sample_name: JSON.stringify($('#sample_name').val()) }, setup_charts);
}
function setup_charts(response) {
    if (response == 'no-progress') {
      return false;
    }
    $('#progress-chart').empty();
    $('#progress-chart-2').empty();
    response_data = JSON.parse(response);
    
    // Mapping chart
    var files = Object.keys(response_data['initials']);
    var text_width = 7*Math.max.apply(Math, $.map(files, function(a) { return a.length }));
    h1 = 300;
    outer_height1 = h1 + 40;
    w1 = 450 - text_width;
    outer_width1 = w1 + text_width + 30;
    x1 = d3.scale.linear().domain([0, 5]).range([0, w1]);
    y1 = d3.scale.ordinal().domain(d3.range(files.length)).rangeBands([0, h1], .2);
    
    var chart = d3.select("#progress-chart").append("svg")
        .attr("class", "chart")
        .attr("width", outer_width1)
        .attr("height", outer_height1)
        .append("g")
        .attr("transform", "translate(" + text_width + ",15)");
        
    var gradient = chart.append("svg:defs")
      .append("svg:linearGradient")
        .attr("id", "gradient")
        .attr("x1", "0%")
        .attr("x2", "100%")
        .attr("spreadMethod", "pad");
    
    gradient.append("svg:stop")
        .attr("offset", "0%")
        .attr("stop-color", "#83b01c")
        .attr("stop-opacity", 1);
    
    gradient.append("svg:stop")
        .attr("offset", "100%")
        .attr("stop-color", "steelblue")
        .attr("stop-opacity", 1);
        
    chart.selectAll("rect")
        .data($.map(new Array(files.length), function(x) { return 0; }))
      .enter().append("rect")
        .attr("y", function(d, i) { return (i) * h1/files.length; })
        .attr("width", x1)
        .attr("height", h1/files.length)
        .style("fill", "url(#gradient)");
    
    chart.append("rect").attr('class', 'bamrect')
        .attr("x", w1-x1(1))
        .attr("y", 0 )
        .attr("width", 0)
        .attr("height", h1 )
        .style("fill", "url(#gradient)");
    chart.selectAll("line")
        .data(x1.ticks(5))
        .enter().append("line")
        .attr("x1", x1)
        .attr("x2", x1)
        .attr("y1", 0)
        .attr("y2", h1)
        .style("stroke", "#ccc");
    
    chart.selectAll(".rule")
        .data(x1.ticks(5))
       .enter().append("text")
         .attr("class", "rule")
         .attr("x", x1)
         .attr("y", 0)
         .attr("dy", -3)
         .attr("text-anchor", "middle")
         .text(function (input) {
                   var labels = {0: 'Start', 1: 'Aligned', 2: 'SAM', 3: 'Raw BAM', 4: 'Sorted BAM', 5: 'Merged BAM'};
                   return labels[input];
              });
    var bars = chart.selectAll("g.bar")
               .data(files)
               .enter().append("svg:g")
               .attr("class", "bar")
               .attr("transform", function(d, i) { return "translate(0," + y1(i) + ")"; });
    bars.append("svg:text")
       .attr("x", 0)
       .attr("y", y1.rangeBand() / 2)
       .attr("dx", -6)
       .attr("dy", ".35em")
       .attr("text-anchor", "end")
       .text(function(d, i) { return files[i]; });
    
    // Cleaning chart
    chroms = get_chroms();
    h2 = 300;
    outer_height2 = h2 + 40;
    w2 = 420;
    outer_width2 = w2 + 80;
    x2 = d3.scale.linear().domain([0, 6]).range([0, w2]);
    y2 = d3.scale.ordinal().domain(d3.range(chroms.length)).rangeBands([0, h2], .2);
    
    var chart = d3.select("#progress-chart-2").append("svg")
        .attr("class", "chart")
        .attr("width", outer_width2)
        .attr("height", outer_height2)
        .append("g")
        .attr("transform", "translate(40,15)");
    
    chart.selectAll("rect")
        .data($.map(new Array(chroms.length), function(x) { return 0; }))
      .enter().append("rect")
        .attr("y", function(d, i) { return (i) * h2/chroms.length; })
        .attr("width", x2)
        .attr("height", h2/chroms.length)
        .style("fill", "url(#gradient)");
    
    chart.selectAll("line")
        .data(x2.ticks(5))
        .enter().append("line")
        .attr("x1", x2)
        .attr("x2", x2)
        .attr("y1", 0)
        .attr("y2", h2)
        .style("stroke", "#ccc");
    
    chart.selectAll(".rule")
        .data(x2.ticks(5))
       .enter().append("text")
         .attr("class", "rule")
         .attr("x", x2)
         .attr("y", 0)
         .attr("dy", -3)
         .attr("text-anchor", "middle")
         .text(function (input) {
                   var labels = {1: 'Split', 2: 'Mark Duplicates', 3: 'Realignment', 4: 'Recalibration', 5: 'Variant Calling', 6: 'Done!'};
                   return labels[input];
              });
     
    var bars = chart.selectAll("g.bar")
               .data(chroms)
               .enter().append("svg:g")
               .attr("class", "bar")
               .attr("transform", function(d, i) { return "translate(0," + y2(i) + ")"; });
    bars.append("svg:text")
       .attr("x", 0)
       .attr("y", y2.rangeBand() / 2)
       .attr("dx", -6)
       .attr("dy", ".35em")
       .attr("text-anchor", "end")
       .text(function(d, i) { return chroms[i]; });
    chart.append("rect").attr('class', 'finalbamrect')
            .attr("x", w2-x2(1))
            .attr("y", 0 )
            .attr("width", 0)
            .attr("height", h2/2 )
            .style("fill", "url(#gradient)");
    chart.append("rect").attr('class', 'vcfrect')
        .attr("x", w2-x2(1))
        .attr("y", h2/2 )
        .attr("width", 0)
        .attr("height", h2/2 )
        .style("fill", "url(#gradient)");
    update_map_chart(response);
}
function update_charts() {
    $.post('check_progress.cgi', { sample_name: JSON.stringify($('#sample_name').val()) }, update_map_chart);
}
function update_map_chart(response){
    if (response == 'no-progress') {
      return false;
    }
    $('.intbamtext').empty()
    $('.finalbamtext').empty()
    $('.vcftext').empty()
    response_data = JSON.parse(response);
    files = Object.keys(response_data['initials']);
    files.sort();
    map_data = [];
    $.each(files, function(i, v) {
        map_data.push(response_data['initials'][v]);
    });
    var chart = d3.select("#progress-chart");
    chart.selectAll("rect")
        .data(map_data)
      .transition().duration(speed)
        .attr("y", function(d, i) { return (i) * h1/map_data.length; })
        .attr("width", x1)
        .attr("height", h1/map_data.length)
        .style("fill", "url(#gradient)");
        
    setTimeout(function() {
      make_merged_bam_chart(response_data)
    }, speed);
}
function make_merged_bam_chart(response_data) {
    $('#download-results').empty();
    var chart = d3.select("#progress-chart");
    if (response_data['outputs']['merged']) {
        chart.select('g').append("text")
                .attr("x", w1-x1(0.5)-18)
                .attr("y", h1/2-10 )
                .text('Int BAM')
                .attr("fill", "white")
                .attr('class', 'link intbamtext')
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        if (response_data['outputs']['merged_stats']) {
            chart.select('g').append("text")
                .attr("x", w1-x1(0.5)-25)
                .attr("y", h1/2+10 )
                .text('Stats done')
                .attr("fill", "white")
                .attr('class', 'link intbamtext')
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        } else {
            chart.select('g').append("text")
                .attr("x", w1-x1(0.5)-35)
                .attr("y", h1/2+10 )
                .text('Running stats...')
                .attr("fill", "white")
                .attr('class', 'intbamtext');
        }
        chart.select('.bamrect')
          .transition().duration(speed)
            .attr("width", x1(1))
            .attr("height", h1 )
            .style("fill", "url(#gradient)");
        $('#download-results').append("<a href='https://console.aws.amazon.com/s3/home' target='_blank'>Download files in your S3 Bucket</a><br/><br/>");
    }
    setTimeout(function() {
      make_clean_chart(response_data)
    }, speed);
}
function make_clean_chart(response_data) {
    data = [];
    chroms = get_chroms();
    $.each(chroms, function(i, v) {
        data.push(response_data['cleans'][v]);
    });
    var chart = d3.select("#progress-chart-2");
    chart.selectAll("rect")
        .data(data)
      .transition().duration(speed)
        .attr("y", function(d, i) { return (i) * h2/data.length; })
        .attr("width", x2)
        .attr("height", h2/data.length)
        .style("fill", "url(#gradient)");
    
    setTimeout(function() {
      make_final_chart(response_data)
    }, speed);
}
function make_final_chart(response_data, chart, w, x, h) {
    var chart = d3.select("#progress-chart-2");
    if (response_data['outputs']['final']) {
        
        chart.select('g').append("text")
                .attr("x", w2-x2(0.5)-10)
                .attr("y", h2/4 - 20)
                .text('BAM')
                .attr("fill", "white")
                .attr('class', 'link finalbamtext')
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        
        if (response_data['outputs']['final_stats']) {
            chart.select('g').append("text")
                .attr("x", w2-x2(0.5)-23)
                .attr("y", h2/4  )
                .text('Stats done')
                .attr("fill", "white")
                .attr('class', 'link finalbamtext')
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        } else {
            chart.select('g').append("text")
                .attr("x", w2-x2(0.5)-35)
                .attr("y", h2/4  )
                .text('Running stats...')
                .attr('class', 'finalbamtext')
                .attr("fill", "white");
        }
        if (response_data['outputs']['depth']) {
            chart.select('g').append("text")
                .attr("x", w2-x2(0.5)-35)
                .attr("y", h2/4 + 20 )
                .text('Depth done')
                .attr("fill", "white")
                .attr('class', 'link finalbamtext')
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        } else {
            chart.select('g').append("text")
                .attr("x", w2-x2(0.5)-35)
                .attr("y", h2/4 + 20 )
                .text('Running depth...')
                .attr('class', 'finalbamtext')
                .attr("fill", "white");
        }
        chart.select('.finalbamrect')
          .transition().duration(speed)
            .attr("width", x2(1))
            .attr("height", h2/2 )
            .style("fill", "url(#gradient)");
    }
    if (response_data['outputs']['vcf']) {
        chart.select('g').append("text")
            .attr("x", w2-x2(0.5)-10)
            .attr("y", 3*h2/4 - 10)
            .text('VCF')
            .attr("fill", "white")
                .attr('class', 'link vcftext');
        if (response_data['outputs']['vcf_eval']) {
            chart.select('g').append("text")
                .attr("x", w2-x2(0.5)-35)
                .attr("y", 3*h2/4 + 10)
                .text('Eval done')
                .attr("fill", "white")
                .attr('class', 'link vcftext')
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        } else {
            chart.select('g').append("text")
                .attr("x", w2-x2(0.5)-35)
                .attr("y", 3*h2/4 + 10)
                .text('Running eval...')
                .attr("fill", "white")
                .attr('class', 'vcftext');
        }
        chart.select('.vcfrect')
          .transition().duration(speed)
            .attr("width", x2(1))
            .attr("height", h2/2 )
            .style("fill", "url(#gradient)");
        $.each($('g > text').filter(function(x) { return $(this).text() == 'VCF' }), function(i, b) {
            b.setAttribute('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
            b.setAttribute('class', 'link');
        })
        if (response_data['outputs']['final']){
            clearInterval(progress_id);
        }
    }
       
}

function get_chroms() {
    var chroms = [];
    for (i = 1; i < 23; i++) {
        chroms.push('chr' + i);
    }
    chroms.push('chrX')
    chroms.push('chrY')
    chroms.push('chrM')
    return chroms;
}

function get_values_from_textarea(pipeline) {
    output_obj = {};
    $.each($('#' + pipeline + '-advanced > textarea'), function(i, v) {
        output_obj[v.id] = $(v).val();
    });
    return output_obj;
}

function get_values_from_checkboxes(pipeline) {
    var output_obj = {};
    $.each($('#' + pipeline + '-advanced > input'), function(i, v) {
        output_obj[v.id] = v.checked;
    });
    return output_obj;
}
function get_all_data() {
    var output = {
        aws_account_number: $('#aws-account-number').val(),
        access_key_id: $('#access-key-id').val(),
        secret_access_key: $('#secret-access-key').val(),
        genome_version: $('#genome-version').val(),
        dbsnp_version: $('#dbsnp-version').val(),
        alignment_pipeline: $('#alignment-pipeline').val(),
        calling_pipeline: $('#calling-pipeline').val(),
        sample_name: $('#sample_name').val(),
        s3_bucket: $('#results-bucket').val(),
        data_type: $('#data-type').val(),
        request_type: $('#amazon-request-types input:checked').val()
    };
    $.extend(output, get_values_from_textarea($('#alignment-pipeline').val()));
    $.extend(output, get_values_from_checkboxes('gatk-clean'));
    $.extend(output, get_values_from_checkboxes($('#calling-pipeline').val()));
    $.extend(output, get_values_from_textarea($('#calling-pipeline').val()));
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
    $('#run-status').empty();
    if (response == 'success') {
        $('#run-status').append('Your jobs are running. You can view the progress and visualize results below.');
        click_refresh_progress();
    } else {
        $('#run-status').append('There was an error: ' + response);
    }
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