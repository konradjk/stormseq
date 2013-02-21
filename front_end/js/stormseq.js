$(document).ready(function(){     
  speed = 500;
  all_samples = [];
  $('#start_button').attr("disabled", false);
  $('#start_button').click(function() {
    $('#start_button').attr("disabled", true);
    $('#run-status').empty();
    var add = $('#sample_name').val().split('\n').length > 1 ? 's' : '';
    $('#run-status').append('Doing final checks and starting cluster' + add + '... <img src="images/busy.gif" /><br/>');
    $('#run-status').append('(This may take several minutes, typically up to 5-10 minutes per sample.)');
    $.post("start_pipeline.cgi", { all_objects: JSON.stringify(get_all_data()) },
      function(response){
        mapping_handle_response(response);
      }
    );
  });
  $('#confirm_cancel_button').click(function() {
    $("#cancel-box").modal('show');
  });
  
  $('#cancel_button').click(function() {
    $('#run-status').empty();
    $.post("cancel_pipeline.cgi", { all_objects: JSON.stringify(get_all_data()) },
      function(response){
        cancel_handle_response(response);
      }
    );
  });
  $('#amazon-request-types > a').click(function() {
    $('#instance-type-description > span').hide();
    setTimeout(function() {
      $('#' + $('#amazon-request-types > a.active').attr('value') + '-description').show();
    }, 20);
  });
  $('#multiple_individuals').click(function() {
    $('#genome_name').hide();
    $('#multiple_genome_names').show();
  });
  $('#single_individual').click(function() {
    $('#genome_name').show();
    $('#multiple_genome_names').hide();
  });
  $('#snap-advanced-link').hide();
  $('#alignment_pipeline').change(function() {
    $('#map-advanced-links > a').hide();
    v = $('#alignment_pipeline').val();
    $('#' + v + '-advanced-link').show();
    if (v == 'bwa') {
      $('.instance-type-text').text('Large');
      $('#instance-type-on-demand-price').text('0.24');
    } else if (v == 'snap') {
      $('.instance-type-text').text('High memory');
      $('#instance-type-on-demand-price').text('1.64');
    }
    refresh_spot_prices();
  });
  $('#samtools-advanced-link').hide();
  $('#calling-pipeline').change(function() {
    $('#call-advanced-links > a').hide();
    v = $('#calling-pipeline').val();
    $('#' + v + '-advanced-link').show();
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
  $('input textarea').autosave({cookieExpiryLength: 30});
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
  $("#progress-charts-" + sample).modal('show');
}
function get_sample_progress_string(sample, response_data) {
  if (sample == 'call_all_samples') {
    if (response_data == null) {
      return "Waiting for samples to finish...";
    } else if (response_data['completed'] == true) {
      return "Done calling all samples together!";
    } else {
      return "Calling all samples together...";
    }
  }
  if (response_data['completed'] == true) {
    return "Done mapping, cleaning, and calling!"
  }
  if (response_data['outputs']['merged'] == 0) {
    return "Mapping...";
  } else {
    if (response_data['outputs']['final'] == 0) {
      return "Mapped. Cleaning...";
    } else {
      if (response_data['outputs']['vcf'] == 0) {
        return "Mapped and cleaned. Calling variants..."
      } else {
        return "Wrapping up analyses..."
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
    $('#all-progress-charts').empty();
    $('#all-progress-charts').append('No jobs are currently running.');
    return false;
  } else {
    $('#start_button').button("option","disabled",true);
  }
  $('#all-progress-charts').empty();
  $('#all-progress-charts-hidden').empty();
  all_response_data = JSON.parse(all_responses);
  $.each(all_response_data, function(sample, response_data) {
    var sample_progress = get_sample_progress_string(sample, response_data);
    if (Object.keys(all_response_data).length > 1) {
      $('#all-progress-charts').append("<span class='qtip-link' id='progress-header-" + sample + "'" +"><b>" + sample + "</b>: " + sample_progress + "</span><br/>");
      var qtip_style = 'qtip-progress';
      if (sample == 'call_all_samples') {
        qtip_style = 'qtip-progress-short';
      }
      if (sample_progress.indexOf('Done') != 0) {
        $("#all-progress-charts-hidden").append("<div class='hidden' id='progress-charts-" + sample + "'" + "'></div>");
        $("#progress-header-" + sample).qtip({
          content: $("#progress-charts-" + sample),
          position: {
            my: 'top left',
            at: 'bottom right'
          },
          hide: {
            fixed: true, // Helps to prevent the tooltip from hiding ocassionally when tracking!
            delay: 240
          },
          style: qtip_style
        });
      }
    } else {
      $('#all-progress-charts').append("<span id='progress-header-" + sample + "'" +"><b>" + sample + "</b>: " + sample_progress + "</span><br/>");
      if (sample_progress.indexOf('Done') != 0) {
        $("#all-progress-charts-hidden").append("<div id='progress-charts-" + sample + "'></div>");
      }
    }
    $("#progress-charts-" + sample).append("<span id='progress-chart-" + sample + "'></span><span id='progress-chart-2-" + sample + "'></span><br/>");
  });
  $.each(all_response_data, function(sample, response_data) {
    if (response_data != null && response_data['completed'] == true) {
      return true;
    }
    if (sample != 'call_all_samples') {
      setup_mapping_chart(sample, response_data);
    }
    setup_cleaning_chart(sample, response_data);
  });
  update_map_charts(all_responses);
}
function setup_mapping_chart(sample, response_data) {
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
}
function setup_cleaning_chart(sample, response_data) {
  // Cleaning chart
  chroms = get_chroms();
  steps = 6;
  if (sample == 'call_all_samples') {
    steps = 2;
  }
  get_dimensions(chroms, steps);
  
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
      .data(x.ticks(steps - 1))
      .enter().append("line")
      .attr("x1", x)
      .attr("x2", x)
      .attr("y1", 0)
      .attr("y2", h)
      .style("stroke", "#ccc");
  
  chart.selectAll(".rule")
      .data(x.ticks(steps - 1))
     .enter().append("text")
       .attr("class", "rule")
       .attr("x", x)
       .attr("y", 0)
       .attr("dy", -3)
       .attr("text-anchor", "middle")
       .text(function (input) {
                if (sample == 'call_all_samples') {
                  var labels = {2: 'Done!'};
                } else {
                  var labels = {1: 'Split', 2: 'Mark Duplicates', 3: 'Realignment', 4: 'Recalibration', 5: 'Variant Calling', 6: 'Done!'};
                }
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
}
function update_charts() {
  $.post('check_progress.cgi', { sample_names: JSON.stringify($('#sample_name').val().split('\n')) }, update_map_charts);
}
function update_map_charts(all_responses){
  if (all_responses == 'not-running') {
    $('#all-progress-charts').empty();
    $('#all-progress-charts').append('No jobs are currently running.');
    return false;
  }
  all_response_data = JSON.parse(all_responses);
  $.each(all_response_data, function(sample, response_data) {
    if (response_data == null || response_data['completed'] == true) {
      return true;
    }
    if (sample == 'call_all_samples') {
      make_clean_chart(sample, response_data);
      return true;
    }
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
  if (sample == 'call_all_samples') {
    get_dimensions(chroms, 1);
  } else {
    get_dimensions(chroms, 6);
  }
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
  if (sample == 'call_all_samples') {
    get_dimensions(chroms, 1);
  } else {
    get_dimensions(chroms, 6);
  }
  if (sample != 'call_all_samples' && response_data['outputs']['final']) {
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
  if ((sample != 'call_all_samples' && response_data['outputs']['vcf']) || (response_data['completed'])) {
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

function get_values_from_inputs() {
  output_obj = {};
  $.each($('input[type!=checkbox].opts'), function(i, v) {
    output_obj[v.id] = $(v).val();
  });
  return output_obj;
}

function get_values_from_checkboxes(pipeline) {
  var output_obj = {};
  $.each($('input[type=checkbox].opts'), function(i, v) {
    output_obj[v.id] = v.checked;
  });
  return output_obj;
}

function get_values_from_selects() {
  var output_obj = {};
  $.each($('select.opts'), function(i, v) {
    output_obj[v.id] = $(v).val();
  });
  return output_obj;
}

function get_all_data() {
  var output = {
    request_type: $('#amazon-request-types > a.active').attr('value'),
    number_of_genomes: $('#number_of_genomes > a.active').attr('value'),
    sample_names: $.map($('select.multi_sample :selected'), function(i) { return($(i).val()); })
  };
  $.extend(output, get_values_from_inputs());
  $.extend(output, get_values_from_checkboxes());
  $.extend(output, get_values_from_selects());
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

function cancel_handle_response(response) {
  $("#cancel-box").modal('hide');
  $('#run-status').empty();
  $('#cancel-response-box').empty();
  $('#cancel-response-box').modal('show');
  if (response == 'success') {
    $('#run-status').append('Your jobs have been cancelled.');
    $('#start_button').button("option","disabled",false);
    $('#cancel-response-box').append('Success! Your jobs have been cancelled!');
    $('#cancel-response-box').append('<br/><br/>If you are finished with STORMSeq, please go to the <a href="https://console.aws.amazon.com/ec2" target="_blank">EC2 console</a> and terminate this running instance (and any others that may still remain)');
  } else if (response == 'success_and_deleted') {
    $('#start_button').button("option","disabled",false);
    $('#run-status').append('Your jobs have been canceled and your S3 bucket deleted.');
    $('#cancel-response-box').append('Success! Your jobs have been cancelled and your S3 bucket deleted!');
    $('#cancel-response-box').append('<br/><br/>If you are finished with STORMSeq, please go to the EC2 console and terminate this running instance (and any others that may still remain)');
  } else if (response == 'wrong-creds') {
    $('#cancel-response-box').append('You have entered incorrect credentials (Access Key ID and Secret Access Key) to stop this server. They must match those given when the cluster was started.');        
    $('#cancel-response-box').append('<br/><br/>The computer used to start these jobs may still have the credentials stored in a cookie. Alternatively, please check and re-enter your credentials from the <a href="https://portal.aws.amazon.com/gp/aws/securityCredentials" target="_blank">Amazon AWS credentials page</a>.');        
    $('#cancel-response-box').append('<br/><br/>Is this your cluster and it is still not cancelling? You may have to manually terminate all the running instances on the <a href="https://console.aws.amazon.com/ec2" target="_blank">EC2 console</a>.');
  } else {
    $('#run-status').append('There was an error: ' + response);
  }
}

function refresh_spot_prices() {
  $('#current-spot-price').html('Loading... <img src="images/busy.gif" />');
  
  $.post("get_current_prices.cgi", { all_objects: JSON.stringify(get_all_data()) },
    function(response){
      prices = response.split(',');
      if ($('.instance-type-text')[0].innerText == 'Large'){
        $('#current-spot-price').html(prices[0]);
      } else {
        $('#current-spot-price').html(prices[1]);
      }
    }
  );
}

function refresh_sample_names() {
  $.post('get_sample_names.cgi', { all_objects: JSON.stringify(get_all_data()) }, function(response) {
    all_samples = response.split(';');
    populate_sample_names();
  });
}

function populate_sample_names() {
  $.each($('.all_samples'), function(a, b) {
    $(b).find('option:gt(0)').remove();
    $.each(all_samples, function(i, v) {
      $(b).append("<option value='" + v + "'>" + v + "</option>");
    });
  });
}

function add_sample() {
  var smax = 0;
  $('#sample_remove').remove();
  $.each($('#sample_name_selects > div'), function(i, a) {
    var next_sample = parseInt(a.id.replace('sample_span_', ''));
    if (next_sample > smax) {
      smax = next_sample;
    };
    smax += 1;
  });
  $('#sample_name_selects').append("<div id='sample_span_" + smax + "'>Sample " + smax + ": \
                                   <select id='sample_" + smax + "' class='input-large multi_sample all_samples'>\
                                   <option value=''></option>\
                                   </select> <a type='button' id='sample_remove' style='font-size: 2.0em; cursor: pointer' onclick='remove_sample(" + smax + ")'>&times;</a>\
                                   </div>\
                                   ");
  $.each(all_samples, function(i, v) {
    $("#sample_" + smax).append("<option value='" + v + "'>" + v + "</option>");
  });
}

function remove_sample(s) {
  $('#sample_span_' + s).remove();
  s = parseInt(s) - 1;
  if (s > 1) {
    $("#sample_span_" + s).append("<a type='button' id='sample_remove' style='font-size: 2.0em; cursor: pointer' onclick='remove_sample(" + s + ")'>&times;</a>");
  }
}