/*
 * A small 3-D surface view for the documentation.
 *
 * It is not a second viewer for production: the browser viewer stays the
 * contour map.  This module takes the same payload, projects the grid with a
 * fixed orthographic camera and draws shaded quads, contour lines and axes as
 * plain SVG.  D3 supplies scales, colours and contours; the projection and the
 * painter's sort are a few dozen lines here.
 */
(function (root, factory) {
    "use strict";
    if (typeof module === "object" && module.exports) {
        module.exports = factory();
    } else {
        root.SurfitSurface3D = factory();
    }
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
    "use strict";

    function decodeGrid(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return new Float64Array(bytes.buffer);
    }

    function analyse(data) {
        const values = typeof data.values === "string" ? decodeGrid(data.values) : data.values;
        const count = values.length;
        const mask = new Uint8Array(count);
        const filled = new Float64Array(count);
        const limit = data.undef * (1 - 1e-6);
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
        return { values: values, mask: mask, filled: filled, min: min, max: max, defined: defined };
    }

    function render(target, data, config, d3) {
        const shape = analyse(data);
        const width = data.count_x;
        const height = data.count_y;
        const size = config.size || 700;
        const pad = 40;
        const azimuth = -Math.PI / 3;
        const elevation = Math.PI / 6;
        const ca = Math.cos(azimuth);
        const sa = Math.sin(azimuth);
        const ce = Math.cos(elevation);
        const se = Math.sin(elevation);
        const zScale = 0.9;

        function worldX(index) { return (index / (width - 1)) * 2 - 1; }
        function worldY(index) { return (index / (height - 1)) * 2 - 1; }
        function worldZ(value) {
            return shape.max === shape.min ? 0.5 : (value - shape.min) / (shape.max - shape.min) * zScale;
        }
        function project(x, y, z) {
            const xr = x * ca - y * sa;
            const yr = x * sa + y * ca;
            return [xr, yr * se + z * ce];
        }

        const projected = [];
        for (let j = 0; j < height; j++) {
            for (let i = 0; i < width; i++) {
                projected.push(project(worldX(i), worldY(j), worldZ(shape.filled[j * width + i])));
            }
        }
        let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
        projected.forEach(function (point) {
            xmin = Math.min(xmin, point[0]); xmax = Math.max(xmax, point[0]);
            ymin = Math.min(ymin, point[1]); ymax = Math.max(ymax, point[1]);
        });
        // Give the axes room outside the surface box.
        xmin -= 0.18; xmax += 0.18; ymin -= 0.2; ymax += 0.18;
        const scale = (size - 2 * pad) / Math.max(xmax - xmin, ymax - ymin);
        const offsetX = pad + (size - 2 * pad - (xmax - xmin) * scale) / 2;
        const offsetY = pad + (size - 2 * pad - (ymax - ymin) * scale) / 2;

        function screen(point) {
            return [offsetX + (point[0] - xmin) * scale,
                    size - offsetY - (point[1] - ymin) * scale];
        }
        function screenWorld(x, y, z) { return screen(project(x, y, z)); }

        const svg = d3.select(target).append("svg")
            .attr("viewBox", [0, 0, size, size])
            .attr("width", "100%")
            .attr("role", "img")
            .attr("aria-label", config.title || "3-D surface");

        const plot = svg.append("g");
        const base = d3.scaleLinear()
            .domain([shape.min, (shape.min + shape.max) / 2, shape.max])
            .range(["#2166ac", "#f7f7f7", "#8c510a"])
            .clamp(true);
        const light = (function () {
            const vector = [-0.35, -0.45, 0.82];
            const norm = Math.hypot.apply(null, vector);
            return vector.map(function (item) { return item / norm; });
        }());

        const stride = Math.max(1, Math.floor(Math.max(width, height) / 60));
        const cells = [];
        for (let j = 0; j + stride < height; j += stride) {
            for (let i = 0; i + stride < width; i += stride) {
                const i1 = Math.min(i + stride, width - 1);
                const j1 = Math.min(j + stride, height - 1);
                const p0 = j * width + i;
                const p1 = j * width + i1;
                const p2 = j1 * width + i1;
                const p3 = j1 * width + i;
                if (!shape.mask[p0] || !shape.mask[p1] || !shape.mask[p2] || !shape.mask[p3]) {
                    continue;
                }
                const x0 = worldX(i), x1 = worldX(i1);
                const y0 = worldY(j), y1 = worldY(j1);
                const z0 = worldZ(shape.filled[p0]);
                const z1 = worldZ(shape.filled[p1]);
                const z2 = worldZ(shape.filled[p2]);
                const z3 = worldZ(shape.filled[p3]);
                const a = [x0, y0, z0], b = [x1, y0, z1];
                const c = [x1, y1, z2], d = [x0, y1, z3];
                const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
                const v = [d[0] - a[0], d[1] - a[1], d[2] - a[2]];
                const normal = [u[1] * v[2] - u[2] * v[1],
                               u[2] * v[0] - u[0] * v[2],
                               u[0] * v[1] - u[1] * v[0]];
                const nlen = Math.hypot.apply(null, normal);
                const intensity = nlen === 0 ? 0.7 :
                    Math.abs((normal[0] * light[0] + normal[1] * light[1] +
                              normal[2] * light[2]) / nlen);
                const value = (shape.filled[p0] + shape.filled[p1] +
                               shape.filled[p2] + shape.filled[p3]) / 4;
                const fill = d3.color(base(value));
                fill.opacity = 1;
                const shade = 0.55 + 0.45 * intensity;
                cells.push({
                    points: [screenWorld(x0, y0, z0), screenWorld(x1, y0, z1),
                             screenWorld(x1, y1, z2), screenWorld(x0, y1, z3)],
                    fill: fill.darker(1.7 - shade).formatHex(),
                    depth: (x0 + x1 + y0 + y1) / 4
                });
            }
        }
        cells.sort(function (left, right) { return left.depth - right.depth; });
        const mesh = plot.append("g").attr("stroke", "#14212b").attr("stroke-opacity", 0.18);
        cells.forEach(function (cell) {
            mesh.append("polygon")
                .attr("points", cell.points.map(function (point) {
                    return point[0].toFixed(2) + "," + point[1].toFixed(2);
                }).join(" "))
                .attr("fill", cell.fill)
                .attr("stroke-width", 0.35);
        });

        // Contours are computed on the same grid and projected onto the surface.
        const thresholdCount = Math.max(4, Math.min(12, config.levels || 10));
        const thresholds = d3.range(thresholdCount).map(function (index) {
            return shape.min + (shape.max - shape.min) * (index + 1) / (thresholdCount + 1);
        });
        const layers = d3.contours().size([width, height]).thresholds(thresholds)(shape.filled);
        function sample(px, py) {
            const gx = Math.max(0, Math.min(width - 1, px - 0.5));
            const gy = Math.max(0, Math.min(height - 1, py - 0.5));
            const i = Math.min(width - 2, Math.floor(gx));
            const j = Math.min(height - 2, Math.floor(gy));
            const tx = gx - i;
            const ty = gy - j;
            const at = function (ii, jj) { return shape.filled[jj * width + ii]; };
            const top = at(i, j) * (1 - tx) + at(i + 1, j) * tx;
            const bottom = at(i, j + 1) * (1 - tx) + at(i + 1, j + 1) * tx;
            return top * (1 - ty) + bottom * ty;
        }
        function isDefined(px, py) {
            const ix = Math.max(0, Math.min(width - 1, Math.round(px - 0.5)));
            const iy = Math.max(0, Math.min(height - 1, Math.round(py - 0.5)));
            return shape.mask[iy * width + ix] === 1;
        }
        function nearestDefinedValue(px, py) {
            const cx = Math.max(0, Math.min(width - 1, Math.round(px - 0.5)));
            const cy = Math.max(0, Math.min(height - 1, Math.round(py - 0.5)));
            for (let radius = 0; radius < 8; radius++) {
                for (let dy = -radius; dy <= radius; dy++) {
                    for (let dx = -radius; dx <= radius; dx++) {
                        if (Math.max(Math.abs(dx), Math.abs(dy)) !== radius)
                            continue;
                        const x = cx + dx;
                        const y = cy + dy;
                        if (x >= 0 && x < width && y >= 0 && y < height &&
                            shape.mask[y * width + x])
                            return shape.filled[y * width + x];
                    }
                }
            }
            return shape.min;
        }
        function contourPath(geometry, checkMask, zValue) {
            let path = "";
            geometry.coordinates.forEach(function (polygon) {
                polygon.forEach(function (ring) {
                    let started = false;
                    let previous = null;
                    ring.forEach(function (point) {
                        const px = point[0], py = point[1];
                        const ok = !checkMask || isDefined(px, py);
                        // A ring can jump across the undefined hole even when
                        // both endpoints are defined; the midpoint catches it.
                        const crosses = checkMask && previous !== null &&
                            !isDefined((previous[0] + px) / 2, (previous[1] + py) / 2);
                        if (!ok) {
                            started = false;
                            previous = point;
                            return;
                        }
                        if (crosses)
                            started = false;
                        const x = (px / (width - 1)) * 2 - 1;
                        const y = (py / (height - 1)) * 2 - 1;
                        const z = worldZ((zValue || sample)(px, py));
                        const projectedPoint = screenWorld(x, y, z);
                        path += (started ? "L" : "M") + projectedPoint[0].toFixed(2) +
                                "," + projectedPoint[1].toFixed(2);
                        started = true;
                        previous = point;
                    });
                });
            });
            return path;
        }
        // Clip the contour lines to the defined region.  Without this, a
        // contour ring of the filled grid runs through the hole where area5 is
        // undefined and leaves short black "hanging" lines over the hole.
        const region = d3.contours()
            .size([width, height])
            .thresholds([0.5])(shape.mask)[0];
        const clipId = "surfit-3d-region";
        if (region) {
            svg.append("defs").append("clipPath")
                .attr("id", clipId)
                .append("path")
                .attr("d", contourPath(region, false))
                .attr("clip-rule", "evenodd");
        }

        const contourGroup = plot.append("g")
            .attr("fill", "none")
            .attr("stroke", "#10202a")
            .attr("stroke-opacity", 0.55)
            .attr("stroke-linejoin", "round")
            .attr("clip-path", region ? "url(#" + clipId + ")" : null);
        layers.forEach(function (layer) {
            contourGroup.append("path")
                .attr("d", contourPath(layer))
                .attr("stroke-width", 0.7);
        });

        // Undefined regions are holes in the mesh.  Fill them in screen
        // space, otherwise the far side of the surface and its contours show
        // through the hole as "hanging" lines.
        const undefinedGrid = new Uint8Array(width * height);
        for (let i = 0; i < undefinedGrid.length; i++)
            undefinedGrid[i] = shape.mask[i] ? 0 : 1;
        const undefinedRegion = d3.contours()
            .size([width, height])
            .thresholds([0.5])(undefinedGrid)[0];
        if (undefinedRegion) {
            plot.append("path")
                .attr("d", contourPath(undefinedRegion, false, nearestDefinedValue))
                .attr("fill", "#ffffff")
                .attr("stroke", "none");
        }

        // Area outlines from the example, projected onto the surface.
        if (data.areas && data.areas.length) {
            const colors = {
                area1: "#2ca02c", area2: "#d62728", area3: "#2ca02c",
                area4: "#d62728", area5: "#555555"
            };
            const areaGroup = plot.append("g")
                .attr("fill", "none")
                .attr("stroke-width", 2.2)
                .attr("stroke-linejoin", "round");
            data.areas.forEach(function (area) {
                let path = "";
                area.points.forEach(function (point) {
                    const x = point[0], y = point[1];
                    const ix = Math.max(0, Math.min(width - 1,
                        Math.round((x - data.min_x) / data.step_x)));
                    const iy = Math.max(0, Math.min(height - 1,
                        Math.round((y - data.min_y) / data.step_y)));
                    const nx = (x - data.min_x) / (data.max_x - data.min_x) * 2 - 1;
                    const ny = (y - data.min_y) / (data.max_y - data.min_y) * 2 - 1;
                    const z = worldZ(shape.filled[iy * width + ix]) + 0.006;
                    const projectedPoint = screenWorld(nx, ny, z);
                    path += (path ? "L" : "M") + projectedPoint[0].toFixed(2) +
                            "," + projectedPoint[1].toFixed(2);
                });
                areaGroup.append("path")
                    .attr("d", path + "Z")
                    .attr("stroke", colors[area.name] || "#333333");
            });
        }

        // Axes: three lines and a handful of labels outside the surface.
        const axis = plot.append("g")
            .attr("stroke", "#26343d")
            .attr("stroke-width", 1);
        const origin = screenWorld(-1.08, -1.08, 0);
        const xEnd = screenWorld(1.12, -1.08, 0);
        const yEnd = screenWorld(-1.08, 1.12, 0);
        const zEnd = screenWorld(-1.08, -1.08, zScale);
        axis.append("line").attr("x1", origin[0]).attr("y1", origin[1])
            .attr("x2", xEnd[0]).attr("y2", xEnd[1]);
        axis.append("line").attr("x1", origin[0]).attr("y1", origin[1])
            .attr("x2", yEnd[0]).attr("y2", yEnd[1]);
        axis.append("line").attr("x1", origin[0]).attr("y1", origin[1])
            .attr("x2", zEnd[0]).attr("y2", zEnd[1]);
        const labels = plot.append("g")
            .attr("font-family", "system-ui, sans-serif")
            .attr("font-size", 11)
            .attr("fill", "#26343d");
        labels.append("text").attr("x", xEnd[0] - 8).attr("y", xEnd[1] + 16).text("x");
        labels.append("text").attr("x", yEnd[0] - 18).attr("y", yEnd[1] - 8).text("y");
        labels.append("text").attr("x", zEnd[0] - 16).attr("y", zEnd[1] - 6).text("z");
        labels.append("text").attr("x", origin[0] - 34).attr("y", origin[1] + 14)
            .text(shape.min.toFixed(1));
        labels.append("text").attr("x", zEnd[0] - 44).attr("y", zEnd[1] + 4)
            .text(shape.max.toFixed(1));

        const legend = d3.select(target).append("div")
            .attr("class", "surfit-legend")
            .style("font", "12px/1.4 system-ui, sans-serif")
            .style("margin-top", "4px");
        legend.text("min " + shape.min.toFixed(3) + "  max " + shape.max.toFixed(3) +
            "  defined " + shape.defined + " / " + shape.values.length);
        return shape;
    }

    return { render: render, decodeGrid: decodeGrid, analyse: analyse };
}));
