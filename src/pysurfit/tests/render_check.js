/*
 * Renders the viewer against a real DOM (jsdom) and reports what came out.
 *
 * This executes render(), not just the contour maths: if the page would draw an
 * empty or malformed map, it shows up here as a missing path or a missing fill.
 *
 * Usage: node render_check.js path/to/viewer.js path/to/data.json out.svg
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const viewerPath = process.argv[2];
const dataPath = process.argv[3];
const outPath = process.argv[4];

const dom = new JSDOM("<!DOCTYPE html><body><div id=\"view\"></div></body>");
global.window = dom.window;
global.document = dom.window.document;

const d3 = require("d3");
const viewer = require(path.resolve(viewerPath));
const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));

const target = document.getElementById("view");
const config = { levels: 10, show_lines: true, size: 820, title: "check" };

const computed = viewer.render(target, data, config, d3);

const svg = target.querySelector("svg");
const bands = target.querySelectorAll("path[data-level]");
const clipped = target.querySelectorAll("clipPath path");
const axisTicks = target.querySelectorAll("svg .tick text");
const readout = target.querySelector(".surfit-readout");
const legend = target.querySelector(".surfit-legend");

// The bands must be painted lowest-first, otherwise the lowest one covers the
// map.  Document order is paint order, so this reads the attribute sequence.
const levels = Array.from(bands).map(function (node) {
    return Number(node.getAttribute("data-level"));
});
const fills = Array.from(bands).map(function (node) {
    return node.getAttribute("fill");
});

const report = {
    has_svg: svg !== null,
    draw_order_ascending: levels.every(function (value, index) {
        return index === 0 || value > levels[index - 1];
    }),
    distinct_fills: new Set(fills).size,
    viewbox: svg ? svg.getAttribute("viewBox") : null,
    bands: bands.length,
    levels: config.levels,
    region_clip: clipped.length,
    axis_ticks: axisTicks.length,
    first_tick: axisTicks.length ? axisTicks[0].textContent : null,
    readout: readout ? readout.textContent : null,
    legend: legend ? legend.textContent : null,
    defined: computed.defined,
    min: computed.min,
    max: computed.max,
    // A band without a fill would draw nothing.
    bands_with_fill: Array.from(bands).filter(function (node) {
        const fill = node.getAttribute("fill");
        return fill && fill !== "none";
    }).length,
    // Every band needs a non-empty path.
    bands_with_path: Array.from(bands).filter(function (node) {
        return (node.getAttribute("d") || "").length > 0;
    }).length,
    // Values at the minimum fall outside every band, so the region is painted
    // with the lowest colour first; without it they show through as holes.
    has_base_fill: target.querySelectorAll("path[data-base]").length
};

if (outPath) {
    fs.writeFileSync(outPath, svg ? svg.outerHTML : "", "utf8");
}

process.stdout.write(JSON.stringify(report));
