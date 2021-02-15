# -*- coding: utf-8 -*-

"""
MPLD3 Plugin to convert a NetworkX graph to a force layout
Copyright (C) 2016 Dheepak Krishnamurthy
"""

import mpld3
from networkx.readwrite.json_graph import node_link_data

class NetworkXD3ForceLayout(mpld3.plugins.PluginBase):
    """A NetworkX to D3 Force Layout Plugin"""

    JAVASCRIPT = """

    mpld3.register_plugin("networkxd3forcelayout", NetworkXD3ForceLayoutPlugin);
    NetworkXD3ForceLayoutPlugin.prototype = Object.create(mpld3.Plugin.prototype);
    NetworkXD3ForceLayoutPlugin.prototype.constructor = NetworkXD3ForceLayoutPlugin;
    NetworkXD3ForceLayoutPlugin.prototype.requiredProps = ["graph",
                                                                "ax_id",];
    NetworkXD3ForceLayoutPlugin.prototype.defaultProps = { coordinates: "data",
                                                               draggable: true,
                                                               gravity: 1,
                                                               charge: -30,
                                                               link_strength: 1,
                                                               friction: 0.9,
                                                               link_distance: 20,
                                                               maximum_stroke_width: 2,
                                                               minimum_stroke_width: 1,
                                                               nominal_stroke_width: 1,
                                                               maximum_radius: 10,
                                                               minimum_radius: 1,
                                                               nominal_radius: 5,
                                                            };

    function NetworkXD3ForceLayoutPlugin(fig, props){
        mpld3.Plugin.call(this, fig, props);
    };

    var color = d3.scale.category20();

    NetworkXD3ForceLayoutPlugin.prototype.zoomScaleProp = function (nominal_prop, minimum_prop, maximum_prop) {
        var zoom = this.ax.zoom;
        scalerFunction = function() {
            var prop = nominal_prop;
            if (nominal_prop*zoom.scale()>maximum_prop) prop = maximum_prop/zoom.scale();
            if (nominal_prop*zoom.scale()<minimum_prop) prop = minimum_prop/zoom.scale();
            return prop
        }
        return scalerFunction;
    }

    NetworkXD3ForceLayoutPlugin.prototype.setupDefaults = function () {

        this.zoomScaleStroke = this.zoomScaleProp(this.props.nominal_stroke_width,
                                                  this.props.minimum_stroke_width,
                                                  this.props.maximum_stroke_width)
        this.zoomScaleRadius = this.zoomScaleProp(this.props.nominal_radius,
                                                  this.props.minimum_radius,
                                                  this.props.maximum_radius)
    }

    NetworkXD3ForceLayoutPlugin.prototype.zoomed = function() {
            this.tick()
        }

    NetworkXD3ForceLayoutPlugin.prototype.draw = function(){

        plugin = this
        brush = this.fig.getBrush();

        DEFAULT_NODE_SIZE = this.props.nominal_radius;

        var height = this.fig.height
        var width = this.fig.width

        var graph = this.props.graph
        var gravity = this.props.gravity.toFixed()
        var charge = this.props.charge.toFixed()
        var link_distance = this.props.link_distance.toFixed()
        var link_strength = this.props.link_strength.toFixed()
        var friction = this.props.friction.toFixed()

        this.ax = mpld3.get_element(this.props.ax_id, this.fig)

        var ax = this.ax;

        this.ax.elements.push(this)

        ax_obj = this.ax;

        var width = d3.max(ax.x.range()) - d3.min(ax.x.range()),
            height = d3.max(ax.y.range()) - d3.min(ax.y.range());

        var color = d3.scale.category20();

        this.xScale = d3.scale.linear().domain([0, 1]).range([0, width]) // ax.x;
        this.yScale = d3.scale.linear().domain([0, 1]).range([height, 0]) // ax.y;

        this.force = d3.layout.force()
                            .size([width, height]);

        this.svg = this.ax.axes.append("g");

        for(var i = 0; i < graph.nodes.length; i++){
            var node = graph.nodes[i];
            if (node.hasOwnProperty('x')) {
                node.x = this.ax.x(node.x);
            }
            if (node.hasOwnProperty('y')) {
                node.y = this.ax.y(node.y);
            }
        }

        this.force
            .nodes(graph.nodes)
            .links(graph.links)
            .linkStrength(link_strength)
            .friction(friction)
            .linkDistance(link_distance)
            .charge(charge)
            .gravity(gravity)
            .start();

        this.link = this.svg.selectAll(".link")
            .data(graph.links)
          .enter().append("line")
            .attr("class", "link")
            .attr("stroke", "black")
            .style("stroke-width", function (d) { return Math.sqrt(d.value); });

        this.node = this.svg.selectAll(".node")
            .data(graph.nodes)
          .enter().append("circle")
            .attr("class", "node")
            .attr("r", function(d) {return d.size === undefined ? DEFAULT_NODE_SIZE : d.size ;})
            .style("fill", function (d) { return d.color; });

        this.node.append("title")
            .text(function (d) { return d.name; });

        this.force.on("tick", this.tick.bind(this));

        this.setupDefaults()
        this.conditional_features(this.svg);

    };

    NetworkXD3ForceLayoutPlugin.prototype.tick = function() {

        this.link.attr("x1", function (d) { return this.ax.x(this.xScale.invert(d.source.x)); }.bind(this))
                 .attr("y1", function (d) { return this.ax.y(this.yScale.invert(d.source.y)); }.bind(this))
                 .attr("x2", function (d) { return this.ax.x(this.xScale.invert(d.target.x)); }.bind(this))
                 .attr("y2", function (d) { return this.ax.y(this.yScale.invert(d.target.y)); }.bind(this));

        this.node.attr("transform", function (d) {
            return "translate(" + this.ax.x(this.xScale.invert(d.x)) + "," + this.ax.y(this.yScale.invert(d.y)) + ")";
            }.bind(this)
        );

    }

    NetworkXD3ForceLayoutPlugin.prototype.conditional_features = function(svg) {

        var drag = d3.behavior.drag()
                .on("dragstart", dragstarted)
                .on("drag", dragged.bind(this))
                .on("dragend", dragended);

        function dragstarted(d) {
            d3.event.sourceEvent.stopPropagation();
            d3.select(this).classed("fixed", d.fixed = true);
            d.fixed = true;
        }

        function dblclick(d) {
          self.force.resume();
          d3.select(this).classed("fixed", d.fixed = false);
        }

        function dragged(d) {
            var mouse = d3.mouse(svg.node());
            d.x = this.xScale(this.ax.x.invert(mouse[0]));
            d.y = this.yScale(this.ax.y.invert(mouse[1]));
            d.px = d.x;
            d.py = d.y;
            d.fixed = true;
            this.force.resume();
        }

        function dragended(d) {
            d.fixed = true;
            }

        var self = this;
        if (this.props.draggable === true) {
            this.node.on("dblclick", dblclick).call(drag)
        }

    }


    """

    def __init__(self, G, pos, ax,
                 gravity=1,
                 link_distance=20,
                 charge=-30,
                 node_size=5,
                 link_strength=1,
                 friction=0.9,
                 draggable=True):

        if pos is None:
            pass

        self.dict_ = {"type": "networkxd3forcelayout",
                      "graph": node_link_data(G),
                      "ax_id": mpld3.utils.get_id(ax),
                      "gravity": gravity,
                      "charge": charge,
                      "friction": friction,
                      "link_distance": link_distance,
                      "link_strength": link_strength,
                      "draggable": draggable,
                      "nominal_radius": node_size}


class PSSTProfilePlot(mpld3.plugins.PluginBase):  # inherit from PluginBase
    """Profile Plot plugin"""

    JAVASCRIPT = """

function createChart() {
    // All options that should be accessible to caller
    var data = [];
    var canvas = [];
    var period = [];

    var updateData;

    function chart(selection){
        selection.each(function () {

            updateData = function() {

                console.log(this)
                d3.select(this).append('svg')
                    .attr('height', height)
                    .attr('width', width)
                    .selectAll('rect')
                    .data(data)
                    .enter()
                    .append('rect')
                    .attr('y', function (d, i) { return i * barSpacing })
                    .attr('height', barHeight)
                    .attr('x', 0)
                    .attr('width', function (d) { return d*widthScale})
                    .style('fill', fillColor);

            }

        });
    }

    chart.data = function(value) {
        if (!arguments.length) return data;
        data = value;
        if (typeof updateData === 'function') updateData();
        return chart;
    };

    chart.canvas = function(value) {
        if (!arguments.length) return canvas;

        canvas = value;
        return chart;
    };

    chart.period = function(value) {
        if (!arguments.length) return period;

        period = value;
        return chart;
    };

    return chart;
}

    mpld3.register_plugin("psstprofileplot", PSSTProfilePlot);
    PSSTProfilePlot.prototype = Object.create(mpld3.Plugin.prototype);
    PSSTProfilePlot.prototype.constructor = PSSTProfilePlot;
    PSSTProfilePlot.prototype.requiredProps = ["data",];
    function PSSTProfilePlot(fig, props){
        mpld3.Plugin.call(this, fig, props);
    };

    PSSTProfilePlot.prototype.draw = function(){

        var data = this.props
        var chart = createChart().canvas(this.fig.canvas).period(0)


    }



    """
    def __init__(self, results):

        self.dict_ = {'type': 'psstprofileplot',
                      'data': json.dumps({'line_power': results.line_power.to_dict(),
                                        'power_generated': results.power_generated.to_dict()})
                     }

fig, ax = plt.subplots()
mpld3.plugins.connect(fig, PSSTProfilePlot(model.results))
if __name__ == "__main__":

    import matplotlib.pyplot as plt
    import networkx as nx

    fig, ax = plt.subplots(1, 1)

    G = nx.Graph()
    G.add_node(1, color='red', x=0.25, y=0.25, fixed=True, name='Node1')
    G.add_node(2, x=0.75, y=0.75, fixed=True)
    G.add_edge(1, 2)
    G.add_edge(1, 3)
    G.add_edge(2, 3)
    pos = None

    mpld3.plugins.connect(fig, NetworkXD3ForceLayout(G, pos, ax))

    with open('test.html', 'w') as f:
        f.write(mpld3.fig_to_html(fig))

    plt.close()
