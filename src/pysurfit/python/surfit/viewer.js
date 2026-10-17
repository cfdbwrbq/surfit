/*
 * surfit viewer: a filled contour map of a gridded surface.
 *
 * Loaded both by the generated HTML page and by the node test, so the contour
 * computation can be checked without a browser.  d3 is passed in rather than
 * imported, which is what makes that possible.
 *
 * Data layout: node values in row-major order, row 0 at min_y (the south edge).
 */
(function (root, factory) {
    "use strict";
    if (typeof module === "object" && module.exports) {
        module.exports = factory();
    } else {
        root.SurfitViewer = factory();
    }
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
    "use strict";

    /* Decodes the little-endian float64 payload the Python side embeds. */
    function decodeGrid(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return new Float64Array(bytes.buffer);
    }

    /* Accepts either the raw array or the base64 payload the page embeds.
     *
     * This matters: a string is indexable and "9" is finite, so passing the
     * encoded payload straight to analyse() silently yields one defined node.
     */
    function asValues(data) {
        if (typeof data.values === "string") {
            return decodeGrid(data.values);
        }
        return data.values;
    }

    /* Splits the payload into a data mask and a value range.
     *
     * Undefined nodes carry the engine's undef_value (FLT_MAX), which would
     * otherwise dominate the colour scale, so they are detected, replaced by
     * the minimum, and covered by a mask polygon instead.
     */
    function analyse(values, undef) {
        const count = values.length;
        const mask = new Float64Array(count);
        const filled = new Float64Array(count);
        const limit = undef * (1 - 1e-6);
        let min = Infinity;
        let max = -Infinity;
        let defined = 0;

        for (let i = 0; i < count; i++) {
            const value = values[i];
            const ok = isFinite(value) && value < limit;
            mask[i] = ok ? 1 : 0;
            if (ok) {
                defined += 1;
                if (value < min) { min = value; }
                if (value > max) { max = value; }
            }
        }
        if (defined === 0) {
            min = 0;
            max = 1;
        }
        for (let i = 0; i < count; i++) {
            filled[i] = mask[i] ? values[i] : min;
        }
        return { mask: mask, filled: filled, min: min, max: max, defined: defined };
    }

    /* Builds the contour layers: one geometry per threshold, plus the outline
     * of the defined region used as a clip path. */
    function computeLayers(data, config, d3) {
        const width = data.count_x;
        const height = data.count_y;
        const values = asValues(data);
        const shape = analyse(values, data.undef);
        const levelCount = config.levels || 12;

        const thresholds = d3.range(levelCount).map(function (index) {
            return shape.min + (shape.max - shape.min) * (index + 1) / (levelCount + 1);
        });

        const layers = d3.contours()
            .size([width, height])
            .thresholds(thresholds)(shape.filled)
            .map(function (layer) {
                return { value: layer.value, polygon: layer };
            });

        const region = d3.contours()
            .size([width, height])
            .thresholds([0.5])(shape.mask);

        return {
            layers: layers,
            region: region[0] || null,
            min: shape.min,
            max: shape.max,
            defined: shape.defined,
            thresholds: thresholds,
            values: values
        };
    }

    function render(target, data, config, d3) {
        const computed = computeLayers(data, config, d3);
        const values = computed.values;
        const width = data.count_x;
        const height = data.count_y;
        const size = config.size || 820;
        const pad = 34;

        const path = d3.geoPath();

        const colour = d3.scaleSequential(d3.interpolateViridis)
            .domain([computed.min, computed.max]);

        const svg = d3.select(target).append("svg")
            .attr("viewBox", [0, 0, size, size])
            .attr("width", "100%")
            .attr("role", "img")
            .attr("aria-label", config.title || "surface");

        const plot = svg.append("g");

        // d3-contour samples the grid at cell centres, so its coordinates run
        // over [0, width] x [0, height] rather than [0, width-1].  The whole
        // plot is drawn in that space and scaled here; row 0 is the south edge,
        // hence the y flip.
        const scaleX = (size - 2 * pad) / width;
        const scaleY = (size - 2 * pad) / height;
        plot.attr("transform", "translate(" + pad + "," + pad + ") " +
            "scale(" + scaleX + "," + scaleY + ") " +
            "translate(0," + height + ") scale(1,-1)");

        const clipId = "surfit-region";
        if (computed.region) {
            svg.append("defs").append("clipPath")
                .attr("id", clipId)
                .append("path")
                .attr("d", path(computed.region) || "");
        }

        const clipped = plot.append("g")
            .attr("clip-path", computed.region ? "url(#" + clipId + ")" : null)
            .attr("stroke", "none");

        // The lowest threshold sits above the minimum, so the nodes at the
        // minimum belong to no band and would show through as holes.  The whole
        // region is laid down in the lowest colour first.
        if (computed.region) {
            clipped.append("path")
                .attr("d", path(computed.region) || "")
                .attr("fill", colour(computed.min))
                .attr("data-base", "1");
        }

        // Each geometry covers the region at or above its threshold, so they
        // are drawn lowest first: every smaller region paints over the larger
        // one beneath it.  Reversing this fills the whole map with the colour
        // of the lowest band.
        computed.layers.forEach(function (layer) {
            clipped.append("path")
                .attr("d", path(layer.polygon) || "")
                .attr("fill", colour(layer.value))
                .attr("data-level", layer.value);
        });

        if (config.show_lines) {
            const lineGroup = plot.append("g")
                .attr("clip-path", computed.region ? "url(#" + clipId + ")" : null)
                .attr("fill", "none")
                .attr("stroke", "#1a1a1a")
                .attr("stroke-opacity", 0.35)
                .attr("vector-effect", "non-scaling-stroke");
            computed.layers.forEach(function (layer) {
                lineGroup.append("path")
                    .attr("d", path(layer.polygon) || "")
                    .attr("stroke-width", 0.6);
            });
        }

        if (computed.region) {
            plot.append("path")
                .attr("d", path(computed.region) || "")
                .attr("fill", "none")
                .attr("stroke", "#444")
                .attr("stroke-width", 1.2)
                .attr("vector-effect", "non-scaling-stroke");
        }

        // Axes: positions are in grid coordinates, so label them with the real
        // world coordinates.
        // The first node sits half a cell in, at contour coordinate 0.5.
        const xAxis = d3.axisBottom(d3.scaleLinear()
            .domain([data.min_x, data.max_x])
            .range([pad + scaleX / 2, size - pad - scaleX / 2]));
        const yAxis = d3.axisLeft(d3.scaleLinear()
            .domain([data.min_y, data.max_y])
            .range([size - pad - scaleY / 2, pad + scaleY / 2]));

        svg.append("g").attr("transform", "translate(0," + (size - pad) + ")")
            .call(function (selection) {
                xAxis(selection);
                selection.selectAll("text").attr("font-size", 10);
            });
        svg.append("g").attr("transform", "translate(" + pad + ",0)")
            .call(function (selection) {
                yAxis(selection);
                selection.selectAll("text").attr("font-size", 10);
            });

        // A readout that follows the pointer.
        const readout = d3.select(target).append("div")
            .attr("class", "surfit-readout")
            .style("font", "12px/1.4 system-ui, sans-serif")
            .style("margin-top", "6px")
            .text("move the pointer over the map");

        svg.on("pointermove", function (event) {
            const bounds = svg.node().getBoundingClientRect();
            const px = (event.clientX - bounds.left) * size / bounds.width;
            const py = (event.clientY - bounds.top) * size / bounds.height;
            const ix = Math.floor((px - pad) / scaleX);
            const iy = Math.floor((py - pad) / scaleY);
            if (ix < 0 || iy < 0 || ix >= width || iy >= height) {
                return;
            }
            const row = height - 1 - iy;
            const value = values[row * width + ix];
            const wx = data.min_x + ix * data.step_x;
            const wy = data.min_y + row * data.step_y;
            const defined = value < data.undef * (1 - 1e-6);
            readout.text("x " + wx.toFixed(2) + "  y " + wy.toFixed(2) +
                "  value " + (defined ? value.toFixed(4) : "undefined"));
        });

        const legend = d3.select(target).append("div")
            .attr("class", "surfit-legend")
            .style("font", "12px/1.4 system-ui, sans-serif")
            .style("margin-top", "4px");
        legend.text("min " + computed.min.toFixed(3) +
            "  max " + computed.max.toFixed(3) +
            "  defined " + computed.defined + " / " + values.length);

        return computed;
    }

    return {
        decodeGrid: decodeGrid,
        analyse: analyse,
        computeLayers: computeLayers,
        render: render
    };
}));
