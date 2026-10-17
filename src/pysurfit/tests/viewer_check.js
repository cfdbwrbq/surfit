/*
 * Runs viewer.js under node with d3 and reports what it produced.
 *
 * The page and this script call the same computeLayers(), so agreeing here
 * means the contour geometry in the browser is the geometry that was checked.
 *
 * Usage: node viewer_check.js path/to/viewer.js < data.json
 */
"use strict";

const path = require("path");
const fs = require("fs");

const viewerPath = process.argv[2];
const d3 = require("d3");
const viewer = require(path.resolve(viewerPath));

const data = JSON.parse(fs.readFileSync(0, "utf8"));

// The page decodes the base64 itself; node has to do it the same way.
function decode(base64) {
    const bytes = Buffer.from(base64, "base64");
    return new Float64Array(bytes.buffer, bytes.byteOffset, bytes.length / 8);
}

const values = decode(data.values);
if (values.length !== data.count_x * data.count_y) {
    throw new Error("decoded " + values.length + " values, expected " +
                    (data.count_x * data.count_y));
}

const config = { levels: 6, show_lines: true };
const computed = viewer.computeLayers(data, config, d3);

let withinBounds = true;
let emptyCount = 0;
function scan(geometry) {
    if (!geometry) { return; }
    const rings = geometry.type === "MultiPolygon"
        ? geometry.coordinates.flat()
        : geometry.coordinates;
    for (const ring of rings) {
        if (!ring || ring.length === 0) { emptyCount += 1; continue; }
        for (const point of ring) {
            // d3-contour works on cell centres, so the domain is [0, count].
            if (point[0] < -0.001 || point[0] > data.count_x + 0.001 ||
                point[1] < -0.001 || point[1] > data.count_y + 0.001) {
                withinBounds = false;
            }
        }
    }
}

for (const layer of computed.layers) { scan(layer.polygon); }
scan(computed.region);

const report = {
    layers: computed.layers.length,
    levels: config.levels,
    thresholds: computed.thresholds.length,
    region: computed.region !== null,
    defined: computed.defined,
    within_bounds: withinBounds,
    empty_rings: emptyCount,
    min: computed.min,
    max: computed.max,
    ascending: computed.thresholds.every(function (value, index, array) {
        return index === 0 || value > array[index - 1];
    })
};

process.stdout.write(JSON.stringify(report));
