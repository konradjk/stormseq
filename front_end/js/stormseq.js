$(document).ready(function(){     
  speed = 500;
  all_samples = [];
  $('.tt').tooltip({
    placement: 'top',
    html: true,
    container: 'body'
  });
  
  $('#start_button').attr("disabled", false);
  $('#start_button').click(check_start_pipeline);
  $('#confirm_cancel_button').click(function() {
    $("#cancel-box").modal('show');
  });
  $('#cancel_button').click(cancel_pipeline);
  
  var dropzone;
  dropzone = document;
  dropzone.addEventListener("dragenter", dragover, false);
  dropzone.addEventListener("dragover", dragover, false);
  dropzone.addEventListener("drop", drop_creds, false);

  $('#amazon-request-types > a').click(function() {
    $('#instance-type-description > span.amazon_types').hide();
    setTimeout(function() {
      $('#' + $('#amazon-request-types > a.active').attr('value') + '-description').show();
    }, 20);
  });
  $('#demo_data').click(function() {
    if ($('#demo_data').is(':checked')) {
      $('#number_of_genomes > a').attr('disabled', 'disabled');
      $('#sample_name').attr('disabled', 'disabled');
    } else {
      $('#number_of_genomes > a').removeAttr('disabled');
      $('#sample_name').removeAttr('disabled');
    }
  });
  $('#multiple_individuals').click(function() {
    $('#genome_name').hide();
    $('#multiple_genome_names').show();
    $('#joint_calling_box').show();
  });
  $('#single_individual').click(function() {
    $('#genome_name').show();
    $('#multiple_genome_names').hide();
    $('#joint_calling_box').hide();
  });
  $('#snap-advanced-link').hide();
  
  $('#alignment_pipeline').change(function() {
    $('#map-advanced-links > a').hide();
    v = $('#alignment_pipeline').val();
    $('#' + v + '-advanced-link').show();
    
    $('#default_instance_option').text('Default (' + instance_normal_prices[default_instances[v]].split(',')[0] + ')');
    //Disable disallowed options
    $('#amazon-instance-types > option[value!="default"]').attr('disabled', 'disabled');
    $.each(allowed_instances[v], function(j, k) {
      $('#amazon-instance-types > option[value="' + k + '"]').removeAttr('disabled');
    });
    //Reset to the default if new option is no longer allowed
    if ($('#amazon-instance-types').find(':selected').attr('disabled') == 'disabled') {
      $('#amazon-instance-types').val('default');
    }
    if ($('#amazon-instance-types').val() == 'default') {
      change_pricing();
    }
  });
  
  $('#amazon-instance-types').change(change_pricing);
  $('#samtools-advanced-link').hide();
  $('#calling_pipeline').change(function() {
    $('#call-advanced-links > a').hide();
    v = $('#calling_pipeline').val();
    v = v.replace('-lite', '');
    $('#' + v + '-advanced-link').show();
    if (v == 'gatk') {
      $('#gvcf_box').show();
    } else {
      $('#gvcf_box').hide();
    }
  });
  refresh_vis();
  click_refresh_progress();
});

var default_instances = {};
default_instances['bwa'] = 'm1.large';
default_instances['bwa-mem'] = 'c1.xlarge';
default_instances['snap'] = 'm2.4xlarge';

var allowed_instances = {};
allowed_instances['bwa'] = ['m1.large', 'm1.xlarge', 'c1.xlarge', 'm2.4xlarge'];
allowed_instances['bwa-mem'] = ['m1.large', 'm1.xlarge', 'c1.xlarge', 'm2.4xlarge'];
allowed_instances['snap'] = ['m2.4xlarge'];

var instance_normal_prices = {};
instance_normal_prices['m1.large'] = 'Large,0.24';
instance_normal_prices['c1.xlarge'] = 'High CPU,0.58';
instance_normal_prices['m1.xlarge'] = 'Extra Large,0.48';
instance_normal_prices['m2.4xlarge'] = 'High memory,1.64';

function dragover(e) {
  e.stopPropagation();
  e.preventDefault();
}
function drop_creds(e) {
  e.stopPropagation();
  e.preventDefault();
  var dt = e.dataTransfer;
  $.each(dt.files, function(i, file) {
    var reader = new FileReader();
    reader.onloadend = function(event) {
      $.each(event.target.result.split('\n'), function(i, v) {
        id = v.split('=')[0];
        value = v.split('=')[1];
        if (id == 'AWSAccessKeyId') {
          $('#access_key_id').val(value);
        } else if (id == 'AWSSecretKey') {
          $('#secret_access_key').val(value);
        } else if (id == 'AccountNumber') {
          $('#aws_account_number').val(value);
        } else if (id == 'S3Bucket') {
          $('#s3_bucket').val(value);
        }
      });
    }
    reader.readAsText(file);
  });
}

function change_pricing() {
  if ($('#amazon-instance-types').val() == 'default') {
    type = default_instances[$('#alignment_pipeline').val()];
  } else {
    type = $('#amazon-instance-types').val();
  }
  $('.instance-type-text').text(instance_normal_prices[type].split(',')[0]);
  $('#instance-type-on-demand-price').text(instance_normal_prices[type].split(',')[1]);
  refresh_spot_prices();
}
function refresh_spot_prices() {
  $('#current-spot-price').html('Loading... <img src="images/busy.gif" />');
  
  $.post("get_current_prices.cgi", { all_objects: JSON.stringify(get_all_data()) },
    function(response){
      $('#current-spot-price').html(response);
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



// Start pipeline helpers
function check_start_pipeline() {
  if ($('#start_button').attr("disabled") == 'disabled') {
    return false;
  }
  // Preparation for license agreements.
  if (false) {
    $('#license_modal_content').load("gatk_license.html");
    $('#license_modal').modal('show');
  } else {
    start_pipeline();
  }
}

function start_pipeline() {
  $('#cancel_button').attr("disabled", true);
  $('#start_button').attr("disabled", true);
  $('#start_tab').collapse('hide');
  $('.run-status').empty();
  $('.run-status').append('Doing final checks and starting clusters... <img src="images/busy.gif" /><br/><br/>');
  $('.run-status').append('(This may take several minutes, typically up to 5-10 minutes per sample.)');
  $.post("start_pipeline.cgi", { all_objects: JSON.stringify(get_all_data()) },
    function(response){
      mapping_handle_response(response);
    }
  );
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
  if ($('#demo_data').is(':checked')) {
    output['number_of_genomes'] = 'single_individual';
    output['sample_name'] = 'exome_demo';
    output['input_s3_bucket'] = 'stormseq_demo';
  } else {
    output['input_s3_bucket'] = output['s3_bucket'];
  }
  return(output);
}

function mapping_handle_response(response) {
  $('.run-status').empty();
  if (response == 'success') {
    $('#run-status').append('Your jobs are running. You can view the progress and visualize results below.');
    click_refresh_progress();
  } else {
    $('.run-status').append('There was an error: ' + response);
  }
}

function cancel_handle_response(response) {
  $("#cancel-box").modal('hide');
  $('#run-status').empty();
  $('#cancel-response-box').empty();
  $('#cancel-response-box').modal('show');
  if (response == 'success') {
    $('#run-status').append('Your jobs have been cancelled.');
    $('#start_button').attr("disabled",false);
    $('#cancel-response-box').append('Success! Your jobs have been cancelled!');
    $('#cancel-response-box').append('<br/><br/>If you are finished with STORMSeq, please go to the <a href="https://console.aws.amazon.com/ec2" target="_blank">EC2 console</a> and terminate this running instance (and any others that may still remain)');
  } else if (response == 'success_and_deleted') {
    $('#start_button').attr("disabled",false);
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


function cancel_pipeline() {
  if ($('#cancel_button').attr("disabled") == 'disabled') {
    return false;
  }
  $('#run-status').empty();
  $.post("cancel_pipeline.cgi", { all_objects: JSON.stringify(get_all_data()) },
    function(response){
      cancel_handle_response(response);
    }
  );
}

// Progress Updating
function click_refresh_progress() {
  $('#all-progress-charts').empty();
  $('#all-progress-charts').append('Checking progress... <img src="images/busy.gif" />');
  $("#all-progress-charts-hidden").empty();
  $.post('check_progress.cgi', {}, setup_charts);
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
  w = 500 - text_width;
  outer_width = w + text_width + 35;
  x = d3.scale.linear().domain([0, steps]).range([0, w]);
  y = d3.scale.ordinal().domain(d3.range(files.length)).rangeBands([0, h], .2);
}

function setup_charts(all_responses) {
  if (all_responses == 'not-running' || all_responses.indexOf('#') == 0) {
    $('#all-progress-charts').empty();
    $('#all-progress-charts').append('No jobs are currently running.');
    return false;
  } else {
    $('#start_button').attr("disabled",true);
    $('#start_tab').collapse('hide');
  }
  $('#all-progress-charts').empty();
  $('#all-progress-charts-hidden').empty();
  all_response_data = JSON.parse(all_responses);
  response_data = all_response_data['samples'];
  acc_class = (Object.keys(response_data).length == 1) ? 'in' : '';
  $.each(response_data, function(sample, sample_response_data) {
    var sample_progress = get_sample_progress_string(sample, sample_response_data);
    if (sample_progress.indexOf('Done') != 0) {
      create_accordion('all-progress-charts', 'progress', sample, acc_class, ': ' + sample_progress);
      $("#progress-" + sample).append("<span id='progress-chart-" + sample + "'></span><span id='progress-chart-2-" + sample + "'></span><br/>");
    }
  });
  $.each(response_data, function(sample, sample_response_data) {
    if (sample_response_data != null && sample_response_data['completed'] == true) {
      return true;
    }
    if (sample != 'call_all_samples') {
      setup_mapping_chart(sample, sample_response_data, all_response_data['alignment_pipeline']);
    }
    setup_cleaning_chart(sample, sample_response_data);
  });
  update_map_charts(all_responses);
}
function setup_mapping_chart(sample, response_data, pipeline) {
  // Mapping chart
  var files = Object.keys(response_data['initials']);
  files.sort();
  get_dimensions(files, 5);
  
  var chart = d3.select("#progress-chart-" + sample).append("svg")
      .attr("class", "chart")
      .attr("width", outer_width)
      .attr("height", outer_height)
      .style("font-size", "0.8em")
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
          if (pipeline == 'bwa') {
            var labels = {0: 'Start', 1: 'Aligned', 2: 'SAM', 3: 'Raw BAM', 4: 'Sorted BAM', 5: 'Merged BAM'};
          } else if (pipeline == 'snap' || pipeline == 'bwa-mem') {
            var labels = {0: 'Start', 1: 'Prepared', 2: 'Aligned', 3: 'Raw BAM', 4: 'Sorted BAM', 5: 'Merged BAM'};
          }
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
  steps = 7;
  if (sample == 'call_all_samples') {
    steps = 2;
  }
  get_dimensions(chroms, steps);
  
  var chart = d3.select("#progress-chart-2-" + sample).append("svg")
      .attr("class", "chart")
      .attr("width", outer_width)
      .attr("height", outer_height)
      .style("font-size", "0.8em")
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
                  var labels = {1: 'Split', 2: 'Mark Duplicates', 3: 'Realign', 4: 'Recalibrate', 5: 'Variant Calls', 6: 'Annotation', 7: 'Done!'};
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
  all_response_data = JSON.parse(all_responses)['samples'];
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
    get_dimensions(chroms, 7);
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
    get_dimensions(chroms, 7);
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



// Visualizations
function refresh_vis() {
  $('#visualize-results').empty();
  $('#visualize-results').append('Refreshing results... <img src="images/busy.gif" />');
  $.post('visualize.cgi', {}, function(response) {
    $('#visualize-results').empty();
    //$('#visualize-results').append(response);
    if (response == '') {
      return false;
    }
    $.each(JSON.parse(response), function(sample, stats) {
      if (stats['merged_stats'] == null) { return false; }
      create_accordion('visualize-results', 'visualize', sample, 'in', '');
      $('#visualize-' + sample).append('<h3>Mapping Statistics</h3>');
      display_qc_stats(sample, stats['merged_stats'], 'Initial');
      
      if (stats['final_stats'] != null) {
        display_qc_stats(sample, stats['final_stats'], 'Final');
      }
      
      if (stats['vcf_stats'] == null) { return false; }
      $('#visualize-' + sample).append('<h3>Variant Statistics</h3>');
      display_snp_density(sample, stats['snp_density']);
      annotation_table(sample, stats['annotation_summary']['annotations']);
      
      $('#visualize-' + sample).append('<h4>SNP Statistics</h4>');
      display_vcf_stats(sample, stats['vcf_stats']);
      
      if (stats['indel_stats'] == null) { return false; }
      $('#visualize-' + sample).append('<h4>Indel Statistics</h4>');
      display_indel_stats(sample, stats['indel_stats']);
    });
  });
}

function create_accordion(location, type, sample, collapsed, additional_text) {
  $('#' + location).append($('<div>', {
    class: 'accordion-group',
    id: type + '-group-' + sample
  }));
  $('#' + type + '-group-' + sample).append($('<div>', {
    class: 'accordion-heading',
    id: type + '-header-' + sample
  }));
  $('#' + type + '-header-' + sample).append($('<a>', {
    class: 'accordion-toggle',
    'data-toggle': 'collapse',
    href: '#' + type + '-body-' + sample,
    html: '<b>' + sample + '</b>' + additional_text
  }));
  $('#' + type + '-group-' + sample).append($('<div>', {
    class: 'accordion-body collapse ' + collapsed,
    id: type + '-body-' + sample
  }));
  $('#' + type + '-body-' + sample).append($('<div>', {
    class: 'accordion-inner',
    id: type + '-' + sample
  }));
}
function display_qc_stats(sample, files, type) {
  all = ['Insert Size Distribution', 'Mapping Quality Distribution', 'Quality by Cycle'];
  $('#visualize-' + sample).append(type + ' BAM: ');
  $.each(all, function(i, v) {
    $('#visualize-' + sample).append($('<a>',{
      text: v,
      href: files[v],
      target: '_blank'
    }));
    if (i != 2) { $('#visualize-' + sample).append(', ') };
  });
  $('#visualize-' + sample).append($('<br/>'));
}

function display_snp_density(sample, files) {
  if (files != null) {
    $('#visualize-' + sample).append($('<a>', {
      href: files[1],
      target: '_blank',
      text: 'Variant Summary Circos Plot'
    }));
    $('#visualize-' + sample).append('<br/>');
    $('#visualize-' + sample).append($('<img>', {
      src: files[0]
    }));
  }
}

function display_vcf_stats(sample, data) {
  variants = data['variants'];
  titv = data['titv'];
  $('#visualize-' + sample).append('SNP Statistics: ' + variants['all'] + ' SNPs called, ');
  $('#visualize-' + sample).append(variants['novel'] + ' of which are novel (' + (variants['novel']*100/variants['all']).toFixed(2) + '%; in ' + data['dbsnp'] + ')<br/>');
  $('#visualize-' + sample).append('Ti/Tv Ratio: ' + titv['all'] + ', (' + titv['novel'] + ' among novel SNPs)<br/>');
}

function display_indel_stats(sample, input_data) {
  length_data = input_data['lengths'];
  insertions = input_data['insertions'];
  deletions = input_data['deletions'];
  $('#visualize-' + sample).append('Insertions: ' + insertions['all'] + ' called, ');
  $('#visualize-' + sample).append(insertions['novel'] + ' of which are novel (' + (insertions['novel']*100/insertions['all']).toFixed(2) + '%)<br/>');
  $('#visualize-' + sample).append('Deletions: ' + deletions['all'] + ' called, ');
  $('#visualize-' + sample).append(deletions['novel'] + ' of which are novel (' + (deletions['novel']*100/deletions['all']).toFixed(2) + '%)<br/>');
  $('#visualize-' + sample).append('Indel length distribution: <div class="btn-group" data-toggle="buttons-radio" id="indel-vis-select-' + sample + '"></div>');
  $.each(['all', 'novel', 'known'], function(i, v) {
    $('#indel-vis-select-' + sample).append($('<a>', {
      class: 'btn btn-primary',
      value: v,
      text: v,
      style: 'text-transform: capitalize',
      onclick: "change_indel_plot('" + sample + "', '" + i + "')"
    }))
  });
  $('#visualize-' + sample).append($('<canvas>', {
    id: 'indel-canvas-' + sample,
    class: 'hide'
  }));
  $('#visualize-' + sample).append($('<a>', {
    id: 'indel-png-' + sample,
    text: ' Save this image',
    download: sample + '_indel_distribution.png',
    target: '_blank'
    //class: 'hide'
  }));
  $('#visualize-' + sample).append($('<div>', {
    id: 'indel-chart-' + sample
  }));
  
  var width = 500;
  var height = 300;
  var padding = 1;
  var margin = {top: 20, right: 0, bottom: 30, left: 40},
    w = width - margin.left - margin.right,
    h = height - margin.top - margin.bottom;
  var formatPercent = d3.format(".0%");
  
  var range = [d3.min(length_data, function(d) { return d[0]; }), d3.max(length_data, function(d) { return d[0]; })];
  
  var x = d3.scale.ordinal()
    .domain(d3.range(range[0], range[1] + 1))
    .rangeRoundBands([0, w], .1);
  var y = d3.scale.linear()
    .domain([0, 1])
    .range([h, 0]);
    
  indel_x = x
  indel_y = y
  indel_h = h
  indel_w = w
  
  var xAxis = d3.svg.axis()
    .scale(x)
    .tickSize(0)
    .tickPadding(6)
    .orient("bottom");
  var yAxis = d3.svg.axis()
    .scale(y)
    .tickSize(0)
    .tickPadding(6)
    .orient("left")
    .tickFormat(formatPercent);
    
  var svg = d3.select('#indel-chart-' + sample).append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr('id', 'indel-chart-g-' + sample)
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
  
  d3.select('#indel-chart-g-' + sample)
    .append('svg:text')
    .attr('id', 'indel-chart-label-' + sample)
    .text('All indels')
    .attr('x', w)
    .attr('text-anchor', 'end');
  
  var rects = svg.selectAll('rect')
    .data(length_data)
    .enter()
    .append('rect')
    .attr('x', function(d) { return x(d[0]); })
    .attr('y', h)
    .attr('width', x.rangeBand())
    .attr('height', 1)
    .attr("fill", "steelblue");
  
  svg.append('g')
    .attr('class', 'x axis')
    .attr("transform", "translate(0," + h + ")")
    .call(xAxis)
    
  svg.append('g')
    .attr('class', 'y axis')
    .call(yAxis)
    .append("text")
  $('#indel-vis-select-' + sample + ' > a[value=all]').trigger('click');
}

function change_indel_plot(sample, type) {
  $('#indel-chart-' + sample).show();
  var rects = d3.select('#indel-chart-g-' + sample).selectAll('rect');
  rects.transition()
    .delay(function(d, i) { return i * 15; })
    .attr("y", function(d) { return indel_y(d[1][type]); })
    .attr("height", function(d) {
      return (indel_h - indel_y(d[1][type]) + 1);
  });
  $('#indel-chart-label-test_sample').text(['All', 'Novel', 'Known'][type] + " indels");
  setTimeout(function() { set_indel_plot_image(sample) }, 500);
}

function set_indel_plot_image(sample) {
  var $container = $('#indel-chart-' + sample);
  content = $container.html().trim();
  canvas = document.getElementById('indel-canvas-' + sample);
  canvg(canvas, content);
  var theImage = canvas.toDataURL('image/png');
  $('#indel-png-' + sample).attr('href', theImage);
}

function annotation_table(sample, data) {
  if (data == null) { return false; }
  $('#visualize-' + sample).append('<br/><h4>Annotations</h4>');
  $('#visualize-' + sample).append($('<table>', {
    id: 'annotation-table-' + sample,
    cellpadding: 4
  }));
  $('#annotation-table-' + sample).append('<tr><th>Annotation</th><th>All Variants</th><th>Known</th><th>Novel</th></tr>');
  $.each(data, function(i, v) {
    var ann = word_to_upper(i).replace(/_/g, ' ');
    $('#annotation-table-' + sample).append('<tr><td>' + ann + '</td><td>' + v['all'] + '</td><td>' + v['known'] + '</td><td>' + v['novel'] + '</td></tr>');
  });
}

function word_to_upper(str) {
  return str.replace(/\b[a-z]/g, function(letter) {
    return letter.toUpperCase();
  });
}