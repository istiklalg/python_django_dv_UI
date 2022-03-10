
Chart.pluginService.register({beforeDraw: function (chart) {
	var width = chart.chart.width,
	height = chart.chart.height,
	ctx = chart.chart.ctx;
	ctx.restore();
	var fontSize = (height / 200).toFixed(2);
	ctx.font = fontSize + "em sans-serif";
	ctx.textBaseline = "middle";
	var text = chart.config.options.elements.center.text,
	textX = Math.round((width - ctx.measureText(text).width) / 2),
	textY = height / 1.65;
	ctx.fillText(text, textX, textY);
	ctx.save();
}});

// colors -> [green, red, orange, blue, yellow, grey, purple]
var chartColors = ['rgba(75, 192, 192, 0.85)','rgba(255, 99, 132, 0.85)','rgba(255, 159, 64, 0.85)','rgba(54, 162, 235, 0.85)','rgba(255, 206, 86, 0.85)','rgba(150, 150, 150, 0.85)','rgba(106, 92, 112, 0.85)']

$(document).ready(function () {
    $(".alert").fadeTo(8000, 0);
    setTimeout(function () {$(".alert").alert("close")}, 10000);
    var elList = document.getElementsByName("charts");
    if(elList.length>0){
        for(var i=0;i<elList.length;i++){
            if(elList[i].lastElementChild.value){
                var dataText = elList[i].lastElementChild.innerHTML;
                var dataStr = (elList[i].lastElementChild.value).replace(/ /g, "").replace("[", "").replace("]", "").split(",");
                var labels = (elList[i].lastElementChild.id).replace(/ /g, "").replace(/'/g,"").replace("[", "").replace("]", "").split(",");
                var centerText = dataStr.reduce(function (total, num){return parseInt(total) + parseInt(num);});
                var colorList = [];
                for(var j=0;j<dataStr.length;j++){colorList.push(chartColors[j]);}
                if(elList[i].firstElementChild.tagName == "CANVAS") {
                    var el = elList[i].firstElementChild;
                    var chartName = elList[i].children[2].innerHTML;
                    if(dataText == "doughnut"){
                        drawDoughnut(el, dataStr, chartName, colorList, labels, centerText);
                    }else if(dataText == "bar"){
                        drawBar(el, dataStr, chartName, colorList, labels);
                    }else if(dataText == "logs_bar"){
                        drawLogsBar(el, dataStr, "Log Counts", colorList[5], labels);
                    }else if(dataText == "line"){
                        drawLine(el, dataStr, chartName, colorList, labels);
                    }else if(dataText == "logs_line"){
                        drawLogsLine(el, dataStr, "Log Counts", colorList[0], labels);
                    }else if(dataText == "simple_logs_line"){
                        drawSimpleLogsLine(el, dataStr, "Log Counts", colorList[0], labels);
                    }else if(dataText == "radar"){
                        drawRadar(el, dataStr, chartName, colorList, labels);
                    }else if(dataText == "polar" || dataText == "polarArea"){
                        drawPolar(el, dataStr, chartName, colorList, labels);
                    }else if(dataText == "bubble" || dataText == "buble"){
                        drawBubble(el, dataStr, chartName, colorList, labels);
                    }else if(dataText == "pie"){
                        drawPie(el, dataStr, chartName, colorList, labels);
                    }else if(dataText == "horizontalBar"){
                        centerText = elList[i].lastElementChild.title;
                        drawHorizontalBar(el, dataStr, chartName, colorList, labels, centerText);
                    }else if(dataText == "doughnut_empty"){
                        drawEmptyDoughnut(el, dataStr, chartName, colorList, labels, chartTitle="", centerText=el.title)
                    }
                }
            }
        }
    }

})


function open_close(button) {
    if(button.tagName=="BUTTON"){
        var div_id = button.name;
        var element = document.getElementById(div_id);
        if(element.style.display=="" || element.style.display=="block"){
                element.style.display = "none";
                //button.innerHTML = "&#10094;";
                button.innerHTML = "&#x002B;";
                button.title = "See Content";
        }else {
                element.style.display = "";
                //button.innerHTML = "&#709;";
                button.innerHTML = "&#8722;";
                button.title = "Close Content";
        }
    }else if(button.tagName=="DIV"){
        var div_id = button.getAttribute("name");
        var element = document.getElementById(div_id);
        if(element.style.display=="" || element.style.display=="block"){
                element.style.display = "none";
        }else {
                element.style.display = "";
        }
    }
}

function open_only(button, name){
    var div_id = button.getAttribute("name");
    var element = document.getElementById(div_id);
    var part_list = document.getElementsByName(name);
    part_list.forEach(function(el){el.style.display = "none";});
    element.style.display = "";

}

function search_it(button) {
    query = button.name;
    url = 'http://www.google.com/search?q=' + query;
    window.open(url,'_blank');
}

function refreshFlow(button) {
    var id = button.name;
    var frame = document.getElementById(id);
    frame.contentWindow.location.reload();
}

function check_and_release_all(name){
    // function take name of checkboxes and check all, release all;
    var checkList = document.getElementsByName(name);
    if(checkList.length > 0){
        var val = checkList[0].checked;
        for(var i=0;i<checkList.length;i++){
            checkList[i].checked = !val;
        }
    }
}

function getClientBrowserName(){
/* This function returns the browser name which client is using */
	var userAgentString = navigator.userAgent;
	// chrome
	var chromeAgent = userAgentString.indexOf("Chrome") > -1;
	// ie
	var IExplorerAgent = userAgentString.indexOf("MSIE") > -1 || userAgentString.indexOf("rv:") > -1;
	// MS Edge
	var edgeAgent = userAgentString.indexOf("Edg") > -1;
	// firefox
	var firefoxAgent = userAgentString.indexOf("Firefox") > -1;
	// Safari
	var safariAgent = userAgentString.indexOf("Safari") > -1;
	// Discard Safari since it also matches Chrome
	if ((chromeAgent) && (safariAgent)) safariAgent = false;
	// Opera
	var operaAgent = userAgentString.indexOf("OP") > -1;
	// Discard Chrome since it also matches Opera        
	if ((chromeAgent) && (operaAgent)) chromeAgent = false;
	if ((chromeAgent) && (edgeAgent)) chromeAgent = false;
	var browserList = [
		{'name': 'Chrome', 'value': chromeAgent},
		{'name': 'IE', 'value': IExplorerAgent},
		{'name': 'Edge', 'value': edgeAgent},
		{'name': 'Safari', 'value': safariAgent},
		{'name': 'Firefox', 'value': firefoxAgent},
		{'name': 'Opera', 'value': operaAgent},
	]
	var browserName;
	browserList.forEach(function (el){if (el.value) browserName = el.name;});
	if(browserName){return browserName}else{return "Unknown"}
}

/* For drawing graphs dynamically */

// for changing graph style;
function changeCharts(type){
    console.log(type);
    var elList = document.getElementsByName("charts");
    if(elList.length>0){
        console.log(elList);
        for(var i=0;i<elList.length;i++){
            var dataStr = (elList[i].lastElementChild.value).replace(/ /g, "").replace("[", "").replace("]", "").split(",");
            var labels = (elList[i].lastElementChild.id).replace(/ /g, "").replace(/'/g,"").replace("[", "").replace("]", "").split(",");
            var centerText = dataStr.reduce(function (total, num){return total + num;});
            var colorList = [];
            for(var j=0;j<dataStr.length;j++){colorList.push(chartColors[j]);}
            if(elList[i].firstElementChild.tagName == "CANVAS") {
                var el = elList[i].firstElementChild;
                var chartName = elList[i].children[2].innerHTML;
                if(type == "doughnut"){
                    drawDoughnut(el, dataStr, chartName, colorList, labels, centerText);
                }else if(type == "bar"){
                    drawBar(el, dataStr, chartName, colorList, labels);
                }else if(type == "line"){
                    drawLine(el, dataStr, chartName, colorList, labels);
                }else if(type == "radar"){
                    drawRadar(el, dataStr, chartName, colorList, labels);
                }else if(type == "polar" || type == "polarArea"){
                    drawPolar(el, dataStr, chartName, colorList, labels);
                }else if(type == "bubble" || type == "buble"){
                    drawBubble(el, dataStr, chartName, colorList, labels);
                }else if(type == "pie"){
                    drawPie(el, dataStr, chartName, colorList, labels);
                }else if(type == "horizontalBar"){
                    drawHorizontalBar(el, dataStr, chartName, colorList, labels);
                }
            }
        }
    }
}

// to draw doughnut graphs;
function drawDoughnut(elm, dataList, chartName, colorList, labels, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1
            }]
        },
        options: {
            cutoutPercentage: 70,
            elements: {
                center: {
                    text: centerText,
                }
            }
        }
    });
}

// to draw doughnut graphs no legend and center text;
function drawEmptyDoughnut(elm, dataList, chartName, colorList, labels, centerText="", chartTitle=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1
            }]
        },
        options: {
            cutoutPercentage: 70,
            title: {
                display: true,
                text: chartTitle
            },
            elements: {
                center: {
                    text: centerText,
                }
            },
            legend: {
                display: false
            }
        }
    });
}

// to draw bar graphs;
function drawBar(elm, dataList, chartName, colorList, labels, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                yAxes: [{ticks: {beginAtZero: true}}]
            },
            elements: {
                center: {
                    text: centerText,
                }
            }
        }
    });
}

// to draw bar graphs for log monitoring screen Elasticsearch logs
function drawLogsBar(elm, dataList, chartName, colorList, labels, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1,
                maxBarThickness: 6,
            }]
        },
        options: {
            scales: {
                xAxes: [{scaleLabel: {display: true, labelString: 'Date & Time (in descending order)'}, ticks: {fontSize: 9}}],
                yAxes: [{scaleLabel: {display: true, labelString: 'Count of Logs'}, ticks: {beginAtZero: true, fontSize: 9}}]
            },
            elements: {
                center: {
                    text: centerText,
                }
            },
        }
    });
}

// to draw line graphs;
function drawLine(elm, dataList, chartName, colorList, labels, stack=false, filling=true, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1,
                fill: filling,
            }]
        },
        options: {
            scales: {
                yAxes: [{stacked: stack, ticks: {beginAtZero: true,}}]
            },
            elements: {
                center: {
                    text: centerText,
                }
            }
        }
    });
}

// to draw line graphs for log monitoring screen Elasticsearch logs
function drawLogsLine(elm, dataList, chartName, colorList, labels, stack=false, filling=true, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1,
                fill: false,
            }]
        },
        options: {
            scales: {
                xAxes: [{scaleLabel: {display: true, labelString: 'Date & Time'}}],
                yAxes: [{scaleLabel: {display: true, labelString: 'Count of Logs'}, ticks: {beginAtZero: true}}]
            },
            elements: {
                center: {
                    text: centerText,
                }
            }
        }
    });
}

// to draw line graphs for log monitoring screen Elasticsearch logs
function drawSimpleLogsLine(elm, dataList, chartName, colorList, labels, stack=false, filling=true, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 0.8,
                lineTension: 0,
                fill: false,
            }]
        },
        options: {
            scales: {
                xAxes: [{scaleLabel: {display: true}}],
                yAxes: [{scaleLabel: {display: true, labelString: 'Counts'}, ticks: {beginAtZero: true}}]
            },
            elements: {
                center: {
                    text: centerText,
                }
            },
            legend: {
                display: false,
            },

        }
    });
}

// to draw radar graphs;
function drawRadar(elm, dataList, chartName, colorList, labels, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1
            }]
        },
        options: {
            elements: {
                center: {
                    text: centerText,
                }
            }
        }
    });
}

// to draw polarArea graphs;
function drawPolar(elm, dataList, chartName, colorList, labels, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1
            }]
        },
        options: {
            elements: {
                center: {
                    text: centerText,
                }
            }
        }
    });
}

// to draw pie graphs;
function drawPie(elm, dataList, chartName, colorList, labels, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1
            }]
        },
        options: {
            elements: {
                center: {
                    text: centerText,
                }
            }
        }
    });
}

// to draw horizontal bar graphs;
function drawHorizontalBar(elm, dataList, chartName, colorList, labels, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'horizontalBar',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList,
                borderColor: colorList,
                borderWidth: 1
            }]
        },
        options: {
            legend: { display: false },
            title: {
                display: true,
                text: centerText
            },
            elements: {
                center: {
                    text: "",
                }
            }
        }
    });
}

// to draw bubble graphs // THIS WILL REWRITE ----------------------------------------------------------;
function drawBubble(elm, dataList, chartName, colorList, labels, centerText=""){
    var ctx = elm.getContext("2d");
    var myChart = new Chart(ctx, {
        type: 'bubble',
        data: {
            labels: labels,
            datasets: [{
                label: chartName,
                data: dataList,
                backgroundColor: colorList[0],
                borderColor: colorList[0],
            }]
        },
        options: {
            elements: {
                center: {
                    text: centerText,
                }
            }
        }
    });
}

// to add bootstrap style alerts with javascript;
function addAlert(message) {
    //$('#alerts').append('<small><div class="alert alert-danger alert-dismissible fade show" role="alert"> <button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ message +'</div></small>');
    $('body').append('<div class="container" id="alerts" style="position:fixed;bottom:0.1%;left:2%;width:30%;zoom:0.75;"><small><div class="alert alert-danger alert-dismissible fade show" role="alert"> <button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+ message +'</div></small></div>');
    $('#alerts').show();
}

//// to zoom rcgraph image ;
//function imageZoom(imgID, resultID) {
//  var img, lens, result, cx, cy;
//  img = document.getElementById(imgID);
//  result = document.getElementById(resultID);
//  /* Creating a lens for zoom area: */
//  lens = document.createElement("DIV");
//  lens.setAttribute("class", "img-zoom-lens");
//  /* Insert lens: */
//  img.parentElement.insertBefore(lens, img);
//  /* Calculate the ratio between result DIV and lens: */
//  cx = result.offsetWidth / lens.offsetWidth;
//  cy = result.offsetHeight / lens.offsetHeight;
//  /* Set background properties for the result DIV */
//  result.style.backgroundImage = "url('" + img.src + "')";
//  result.style.backgroundSize = (img.width * cx) + "px " + (img.height * cy) + "px";
//  /* Execute a function when someone moves the cursor over the image, or the lens: */
//  lens.addEventListener("mousemove", moveLens);
//  img.addEventListener("mousemove", moveLens);
//  /* And also for touch screens: */
//  lens.addEventListener("touchmove", moveLens);
//  img.addEventListener("touchmove", moveLens);
//  function moveLens(e) {
//    var pos, x, y;
//    /* Prevent any other actions that may occur when moving over the image */
//    e.preventDefault();
//    /* Get the cursor's x and y positions: */
//    pos = getCursorPos(e);
//    /* Calculate the position of the lens: */
//    x = pos.x - (lens.offsetWidth / 2);
//    y = pos.y - (lens.offsetHeight / 2);
//    /* Prevent the lens from being positioned outside the image: */
//    if (x > img.width - lens.offsetWidth) {x = img.width - lens.offsetWidth;}
//    if (x < 0) {x = 0;}
//    if (y > img.height - lens.offsetHeight) {y = img.height - lens.offsetHeight;}
//    if (y < 0) {y = 0;}
//    /* Set the position of the lens: */
//    lens.style.left = x + "px";
//    lens.style.top = y + "px";
//    /* Display what the lens "sees": */
//    result.style.backgroundPosition = "-" + (x * cx) + "px -" + (y * cy) + "px";
//  }
//  function getCursorPos(e) {
//    var a, x = 0, y = 0;
//    e = e || window.event;
//    /* Get the x and y positions of the image: */
//    a = img.getBoundingClientRect();
//    /* Calculate the cursor's x and y coordinates, relative to the image: */
//    x = e.pageX - a.left;
//    y = e.pageY - a.top;
//    /* Consider any page scrolling: */
//    x = x - window.pageXOffset;
//    y = y - window.pageYOffset;
//    return {x : x, y : y};
//  }
//}


