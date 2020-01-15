function visualize(json) {

var margin = {top: -5, right: -5, bottom: -5, left: -5};
    var width = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
    var height = 800 ;

    var w = width - margin.left - margin.right,
        h = height- margin.top - margin.bottom;

    var fill = d3.scale.category20();

  var svg = d3.select("#graph").append("svg")
      .attr("width", w)
      .attr("height", h)

  var g = svg
      .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.right + ")");

  var container = g.append("g");

  var min_zoom = 0.1;
  var max_zoom = 7;
  var zoom = d3.behavior.zoom().scaleExtent([min_zoom,max_zoom])

  var force = d3.layout.force()
      .charge(function(node) {return node._type == 'gen'? -3000 : -3000; })
      .linkDistance(function(link) { return link._type == 'branch'? 50 : 25; })
      .linkStrength(function(link) { return link._type == 'branch'? 1: 1; })
      .nodes(json.nodes)
      .links(json.links)
      .size([w, h])
      .gravity(.5)
      .start();

  var link = container.selectAll("line.link")
      .data(json.links)
    .enter().append("svg:line")
      .attr("class", "link")
      .style("stroke-width", function(d) { return Math.sqrt(d.value); })
      .attr("x1", function(d) { return d.source.x; })
      .attr("y1", function(d) { return d.source.y; })
      .attr("x2", function(d) { return d.target.x; })
      .attr("y2", function(d) { return d.target.y; });


    var tooltip = d3.select("body")
        .append("div")
        .attr("class", "tooltip")
        .style("position", "absolute")
        .style("z-index", "10")
        .style("visibility", "hidden")
        .text("a simple tooltip")
        .attr("class", "outlinetext")


  var gnodes = container.selectAll("circle.node")
      .data(json.nodes)
    .enter().append('g')
    
  var node = gnodes.append("svg:circle")
      .attr("class", "node")
      .attr("r", function(d) { return d._type == 'gen'? 5: 10})
      .style("fill", function(d) { return d._type == 'gen'? 'red' : 'blue'; })
      .on("mouseover", function(d){
          var appendString = '';
          for(var k in d){
              if(k == '_type') {continue; }
              if(k == 'x') {continue; }
              if(k == 'y') {continue; }
              if(k == 'px') {continue; }
              if(k == 'py') {continue; }
            appendString += "" + k + ":" + d[k] + '\n';
          }
          tooltip.text(appendString);
          return tooltip.style("visibility", "visible");})
      .on("mousemove", function(d){return tooltip.style("top",
          (d3.event.pageY-10)+"px").style("left",(d3.event.pageX+10)+"px");})
      .on("mouseout", function(d){return tooltip.style("visibility", "hidden");});


  var labels = gnodes.append("text")
      .attr("dx", 12)
      .attr("dy", ".35em")
      .text(function(d) { return d.id });


  container.style("opacity", 1e-6)
    .transition()
      .duration(1000)
      .style("opacity", 1);

  force.on("tick", function() {
    link.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    gnodes.attr("transform", function(d) { return 'translate(' + [d.x, d.y] + ')'; });

  });


zoom.on("zoom", function() {
    g.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
});

svg.call(zoom);

}

