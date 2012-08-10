$(document).ready(function(){     
    speed = 500;
    $('#start_button').button({disabled:false});
    $('#start_button').click(function() {
        $(this).button('disable');
        $('#run-status').empty();
        var add = ''
        if ($('#sample_name').val().split('\n').length > 1) {
          add = 's'
        }
        $('#run-status').append('Doing final checks and starting cluster' + add + '... <img src="images/busy.gif" /><br/>');
        $('#run-status').append('(This may take several minutes, typically up to 5-10 minutes per sample.)');
        $.post("start_pipeline.cgi", { all_objects: JSON.stringify(get_all_data()) },
            function(response){
                mapping_handle_response(response);
            }
        );
    });
    $("#amazon-request-types").buttonset();
    $("#force-machine-type").buttonset();
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
    refresh_vis();
    click_refresh_progress();
});

function refresh_vis() {
    $('#visualize-results').empty();
    $('#visualize-results').append('Refreshing results... <img src="images/busy.gif" />');
    $.post('visualize.cgi', { sample_names: JSON.stringify($('#sample_name').val().split('\n')) }, function(response) {
      $('#visualize-results').empty();
      $('#visualize-results').append(response);
    });
}

function indel_length_chart() {
    var data = google.visualization.arrayToDataTable([
      ['Year', 'Sales', 'Expenses'],
      ['2004',  1000,      400],
      ['2005',  1170,      460],
      ['2006',  660,       1120],
      ['2007',  1030,      540]
    ]);

    var options = {
      hAxis: {title: 'Indel Length'},
      bar:   { groupWidth: "100%" },
      colors:['steelblue','#83b01c']
    };

    var chart = new google.visualization.ColumnChart(document.getElementById('chart_div'));
    chart.draw(data, options);
}

function click_refresh_progress() {
    $('#all-progress-charts').empty();
    $('#all-progress-charts').append('Checking progress... <img src="images/busy.gif" />');
    $("#all-progress-charts-hidden").empty();
    $.post('check_progress.cgi', { sample_names: JSON.stringify($('#sample_name').val().split('\n')) }, setup_charts);
}
function show_progress_chart(sample) {
  $("#progress-charts-" + sample).dialog({ modal: true, width: "80%", resizable: false, buttons: {
    "Close": function() {$(this).dialog("close");}
    }});
}
function get_sample_progress_string(response_data) {
  if (response_data['outputs']['merged'] == 0) {
    return "Mapping...";
  } else {
    if (response_data['outputs']['final'] == 0) {
      return "Mapped. Cleaning...";
    } else {
      if (response_data['outputs']['vcf'] == 0) {
        return "Mapped and cleaned. Calling variants..."
      } else {
        return "Done mapping, cleaning, and calling!"
      }
    }
  }
}

function get_dimensions(files, steps) {
  text_width = 7*Math.max.apply(Math, $.map(files, function(a) { return a.length }));
  h = 300;
  outer_height = h + 40;
  w = 450 - text_width;
  outer_width = w + text_width + 30;
  x = d3.scale.linear().domain([0, steps]).range([0, w]);
  y = d3.scale.ordinal().domain(d3.range(files.length)).rangeBands([0, h], .2);
}

function setup_charts(all_responses) {
  if (all_responses == 'not-running') {
    return false;
  } else {
    $('#start_button').button("option","disabled",true);
  }
  $('#all-progress-charts').empty();
  all_response_data = JSON.parse(all_responses);
  $.each(all_response_data, function(sample, response_data) {
    var sample_progress = get_sample_progress_string(response_data);
    if (Object.keys(all_response_data).length > 1) {
      $('#all-progress-charts').append("<span class='qtip-link' id='progress-header-" + sample + "'" +"><b>" + sample + "</b>: " + sample_progress + "</span><br/>");
      $("#all-progress-charts-hidden").append("<div class='hidden' id='progress-charts-" + sample + "'" + "'></div>");
      $("#progress-header-" + sample).qtip({
        content: $("#progress-charts-" + sample),
        position: {
          my: 'top left',
          at: 'bottom right'
          //viewport: $(window), // Keep it on-screen at all times if possible
          //adjust: {
          //  x: 10,  y: 10
          //}
        },
        hide: {
          fixed: true, // Helps to prevent the tooltip from hiding ocassionally when tracking!
          delay: 240
        },
        style: 'qtip-progress'
      });
    } else {
      $('#all-progress-charts').append("<span id='progress-header-" + sample + "'" +"><b>" + sample + "</b>: " + sample_progress + "</span><br/>");
      $("#all-progress-charts-hidden").append("<div id='progress-charts-" + sample + "'></div>");
    }
    $("#progress-charts-" + sample).append("<span id='progress-chart-" + sample + "'></span><span id='progress-chart-2-" + sample + "'></span><br/>");
  });
  $.each(all_response_data, function(sample, response_data) {
    // Mapping chart
    var files = Object.keys(response_data['initials']);
    files.sort();
    get_dimensions(files, 5);
    
    var chart = d3.select("#progress-chart-" + sample).append("svg")
        .attr("class", "chart")
        .attr("width", outer_width)
        .attr("height", outer_height)
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
        .attr("y", function(d, i) { return (i) * h/files.length; })
        .attr("width", x)
        .attr("height", h/files.length)
        .style("fill", "url(#gradient)");
    
    chart.append("rect").attr('class', 'bamrect ' + sample)
        .attr("x", w-x(1))
        .attr("y", 0 )
        .attr("width", 0)
        .attr("height", h )
        .style("fill", "url(#gradient)");
    chart.selectAll("line")
        .data(x.ticks(5))
        .enter().append("line")
        .attr("x1", x)
        .attr("x2", x)
        .attr("y1", 0)
        .attr("y2", h)
        .style("stroke", "#ccc");
    
    chart.selectAll(".rule")
        .data(x.ticks(5))
       .enter().append("text")
         .attr("class", "rule")
         .attr("x", x)
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
               .attr("transform", function(d, i) { return "translate(0," + y(i) + ")"; });
    bars.append("svg:text")
       .attr("x", 0)
       .attr("y", y.rangeBand() / 2)
       .attr("dx", -6)
       .attr("dy", ".35em")
       .attr("text-anchor", "end")
       .text(function(d, i) { return files[i]; });
    
    // Cleaning chart
    chroms = get_chroms();
    get_dimensions(chroms, 6);
    
    var chart = d3.select("#progress-chart-2-" + sample).append("svg")
        .attr("class", "chart")
        .attr("width", outer_width)
        .attr("height", outer_height)
        .append("g")
        .attr("transform", "translate(40,15)");
    
    chart.selectAll("rect")
        .data($.map(new Array(chroms.length), function(x) { return 0; }))
      .enter().append("rect")
        .attr("y", function(d, i) { return (i) * h/chroms.length; })
        .attr("width", x)
        .attr("height", h/chroms.length)
        .style("fill", "url(#gradient)");
    
    chart.selectAll("line")
        .data(x.ticks(5))
        .enter().append("line")
        .attr("x1", x)
        .attr("x2", x)
        .attr("y1", 0)
        .attr("y2", h)
        .style("stroke", "#ccc");
    
    chart.selectAll(".rule")
        .data(x.ticks(5))
       .enter().append("text")
         .attr("class", "rule")
         .attr("x", x)
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
               .attr("transform", function(d, i) { return "translate(0," + y(i) + ")"; });
    bars.append("svg:text")
       .attr("x", 0)
       .attr("y", y.rangeBand() / 2)
       .attr("dx", -6)
       .attr("dy", ".35em")
       .attr("text-anchor", "end")
       .text(function(d, i) { return chroms[i]; });
    chart.append("rect").attr('class', 'finalbamrect ' + sample)
            .attr("x", w-x(1))
            .attr("y", 0 )
            .attr("width", 0)
            .attr("height", h/2 )
            .style("fill", "url(#gradient)");
    chart.append("rect").attr('class', 'vcfrect ' + sample)
        .attr("x", w-x(1))
        .attr("y", h/2 )
        .attr("width", 0)
        .attr("height", h/2 )
        .style("fill", "url(#gradient)");
    if (typeof progress_id === 'undefined') {
      progress_id = setInterval(update_charts, 300000);
    }
  });
  update_map_charts(all_responses);
}
function update_charts() {
    $.post('check_progress.cgi', { sample_names: JSON.stringify($('#sample_name').val().split('\n')) }, update_map_charts);
}
function update_map_charts(all_responses){
  if (all_responses == 'not-running') {
    return false;
  }
  all_response_data = JSON.parse(all_responses);
  $.each(all_response_data, function(sample, response_data) {
    $('.intbamtext.' + sample).empty()
    $('.finalbamtext.' + sample).empty()
    $('.vcftext.' + sample).empty()

    files = Object.keys(response_data['initials']);
    files.sort();
    get_dimensions(files, 5);
    var map_data = [];
    $.each(files, function(i, v) {
        map_data.push(response_data['initials'][v]);
    });
    //console.log('Sample: ', sample, 'Amount of data: ', files.length);
    //console.log('Data: ', response_data['initials']);
    var chart = d3.select("#progress-chart-" + sample);
    var file_length = files.length;
    chart.selectAll("rect")
        .data(map_data)
      .transition().duration(speed)
    //    .attr("y", function(d, i) { console.log('Sample: ', sample, 'File: ', i, 'Map length: ', file_length); console.log((i) * h/file_length); return (i) * h/file_length; })
        .attr("y", function(d, i) { return (i) * h/file_length; })
        .attr("width", x)
        .attr("height", h/file_length)
        .style("fill", "url(#gradient)");
        
    setTimeout(function() {
      make_merged_bam_chart(sample, response_data)
    }, speed);
  });
}
function make_merged_bam_chart(sample, response_data) {
    files = Object.keys(response_data['initials']);
    files.sort();
    get_dimensions(files, 5);
    $('#download-results').empty();
    var chart = d3.select("#progress-chart-" + sample);
    if (response_data['outputs']['merged']) {
        refresh_vis();
        chart.select('g').append("text")
                .attr("x", w-x(0.5)-18)
                .attr("y", h/2-10 )
                .text('Int BAM')
                .attr("fill", "white")
                .attr('class', 'link intbamtext ' + sample)
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        if (response_data['outputs']['merged_stats']) {
            chart.select('g').append("text")
                .attr("x", w-x(0.5)-25)
                .attr("y", h/2+10 )
                .text('Stats done')
                .attr("fill", "white")
                .attr('class', 'link intbamtext ' + sample)
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        } else {
            chart.select('g').append("text")
                .attr("x", w-x(0.5)-35)
                .attr("y", h/2+10 )
                .text('Running stats...')
                .attr("fill", "white")
                .attr('class', 'intbamtext ' + sample);
        }
        chart.select('.bamrect.' + sample)
          .transition().duration(speed)
            .attr("width", x(1))
            .attr("height", h )
            .style("fill", "url(#gradient)");
        $('#download-results').append("<a href='https://console.aws.amazon.com/s3/home' target='_blank'>Download files in your S3 Bucket</a><br/><br/>");
    }
    setTimeout(function() {
      make_clean_chart(sample, response_data)
    }, speed);
}
function make_clean_chart(sample, response_data) {
    data = [];
    chroms = get_chroms();
    $.each(chroms, function(i, v) {
        data.push(response_data['cleans'][v]);
    });
    get_dimensions(chroms, 6);
    var chart = d3.select("#progress-chart-2-" + sample);
    chart.selectAll("rect")
        .data(data)
      .transition().duration(speed)
        .attr("y", function(d, i) { return (i) * h/data.length; })
        .attr("width", x)
        .attr("height", h/data.length)
        .style("fill", "url(#gradient)");
    
    setTimeout(function() {
      make_final_chart(sample, response_data)
    }, speed);
}
function make_final_chart(sample, response_data) {
    var chart = d3.select("#progress-chart-2-" + sample);
    chroms = get_chroms();
    get_dimensions(chroms, 6);
    if (response_data['outputs']['final']) {
        
        chart.select('g').append("text")
                .attr("x", w-x(0.5)-10)
                .attr("y", h/4 - 20)
                .text('BAM')
                .attr("fill", "white")
                .attr('class', 'link finalbamtext ' + sample)
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        
        if (response_data['outputs']['final_stats']) {
            chart.select('g').append("text")
                .attr("x", w-x(0.5)-24)
                .attr("y", h/4  )
                .text('Stats done')
                .attr("fill", "white")
                .attr('class', 'link finalbamtext ' + sample)
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        } else {
            chart.select('g').append("text")
                .attr("x", w-x(0.5)-35)
                .attr("y", h/4  )
                .text('Running stats...')
                .attr('class', 'finalbamtext ' + sample)
                .attr("fill", "white");
        }
        if (response_data['outputs']['depth']) {
            chart.select('g').append("text")
                .attr("x", w-x(0.5)-25)
                .attr("y", h/4 + 20 )
                .text('Depth done')
                .attr("fill", "white")
                .attr('class', 'link finalbamtext ' + sample)
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        } else {
            chart.select('g').append("text")
                .attr("x", w-x(0.5)-35)
                .attr("y", h/4 + 20 )
                .text('Running depth...')
                .attr('class', 'finalbamtext ' + sample)
                .attr("fill", "white");
        }
        chart.select('.finalbamrect.' + sample)
          .transition().duration(speed)
            .attr("width", x(1))
            .attr("height", h/2 )
            .style("fill", "url(#gradient)");
    }
    if (response_data['outputs']['vcf']) {
        chart.select('g').append("text")
            .attr("x", w-x(0.5)-10)
            .attr("y", 3*h/4 - 10)
            .text('VCF')
            .attr("fill", "white")
                .attr('class', 'link vcftext ' + sample);
        if (response_data['outputs']['vcf_eval']) {
            chart.select('g').append("text")
                .attr("x", w-x(0.5)-24)
                .attr("y", 3*h/4 + 10)
                .text('Eval done')
                .attr("fill", "white")
                .attr('class', 'link vcftext ' + sample)
                .attr('onclick', 'window.open("https://console.aws.amazon.com/s3/home")');
        } else {
            chart.select('g').append("text")
                .attr("x", w-x(0.5)-35)
                .attr("y", 3*h/4 + 10)
                .text('Running eval...')
                .attr("fill", "white")
                .attr('class', 'vcftext ' + sample);
        }
        chart.select('.vcfrect.' + sample)
          .transition().duration(speed)
            .attr("width", x(1))
            .attr("height", h/2 )
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
        sample_names: $('#sample_name').val().split('\n'),
        s3_bucket: $('#results-bucket').val(),
        data_type: $('#data-type').val(),
        request_type: $('#amazon-request-types input:checked').val(),
        force_large_machine: $('#force-machine-type input:checked').val(),
        indel_calling: $('#call_indels')[0].checked,
        sv_calling: $('#call_svs')[0].checked,
        joint_calling: false
    };
    $.extend(output, get_values_from_textarea($('#alignment-pipeline').val()));
    $.extend(output, get_values_from_checkboxes('gatk-clean'));
    $.extend(output, get_values_from_checkboxes($('#calling-pipeline').val()));
    $.extend(output, get_values_from_textarea($('#calling-pipeline').val()));
    $.extend(output, get_values_from_textarea('amazon'));
    return(output);
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
            $('#large-current-price').html(prices[0]);
            $('#hi-mem-current-price').html(prices[1]);
        }
    );
}