
// charts in profile
function set_new_chart(cite_by_year,concept_score) {
    // Set chart options
    var bar_options = {
        legend: {display: false},
        scales: {
            xAxes: [{
                ticks: {
                    minRotation: 0,
                    maxRotation: 0,
                    callback: function(value, index, values) {
                        
                        if (index === 0 || index === values.length - 1) {
                        return value;
                        } else {
                        return null;
                        }
                    }
                }
            }],
            yAxes: [{
                display: false,
                suggestedMax: 50
            }]
        },
        layout: {
            padding: {
                top: 5
            }
        },
        tooltips: {
            callbacks: {
                label: function(tooltipItem) {
                    var xLabel = tooltipItem.xLabel;
                    var yLabel = tooltipItem.yLabel;
                    return xLabel + ': ' + yLabel;
                }
            }
        },
    };
    // Prepare data for the bar chart
    const x_year = [];
    const y_work = [];
    cite_by_year = cite_by_year.reverse()
    for (var i = 0; i < cite_by_year.length; i++) {
        x_year.push(cite_by_year[i]["year"]);
        if ("works_count" in cite_by_year[i]) {
            y_work.push(cite_by_year[i]["works_count"]);
        }
        else if ("cited_by_count" in cite_by_year[i]) {
            y_work.push(cite_by_year[i]["cited_by_count"]);
        }
    }

    // Set data for the bar chart
    var bardata = {
        labels: x_year,
        datasets: [{
            data: y_work,
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 1
        }]
    };
    // Initialize bar chart
    var ctx = document.getElementById('myBarChart').getContext('2d');
    myBarChart = new Chart(ctx, {
        type: 'bar',
        data: bardata,
        options: bar_options
    });

    // Set options for the polar chart
    var polaroptions = {
        legend: {display: false},
        scale: {
            ticks: {
                beginAtZero: true
            }
        },
    };   

    // Set data for the polar chart
    // 'rgba(54, 162, 235, 0.5)',
    //         'rgba(255, 206, 86, 0.5)',
    //         'rgba(75, 192, 192, 0.5)',
    //         'rgba(229, 159, 132, 0.5)',
    //         'rgba(201, 162, 217, 0.5)',
    //         'rgba(81, 255, 183, 0.5)'
    const polardata = {
        labels: concept_score['concept_name'],
        datasets: [{
        data: concept_score['score'],
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 1
        }]
    };

    // Initialize polar chart
    var polar_ctx = document.getElementById('myPolarChart').getContext('2d');
    myPolarChart = new Chart(polar_ctx, {
                    type: 'polarArea',
                    data: polardata,
                    options: polaroptions
                });

    return myBarChart,myPolarChart;
}
