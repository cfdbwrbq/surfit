/*
 * Renders a viewer payload to a standalone SVG file, for the documentation.
 *
 * The same viewer.js the page runs, so a figure cannot drift from what
 * save_viewer() produces.
 *
 * Usage: node render_svg.js viewer.js data.json out.svg
 *   SIZE=820 LEVELS=12 LINES=1 TITLE="..." in the environment.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const dom = new JSDOM("<!DOCTYPE html><body><div id=\"figure\"></div></body>");
global.window = dom.window;
global.document = dom.window.document;

const d3 = require("d3");

const viewerPath = process.argv[2];
const dataPath = process.argv[3];
const outPath = process.argv[4];

const viewer = require(path.resolve(viewerPath));
const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));

const config = {
    levels: Number(process.env.LEVELS || 12),
    size: Number(process.env.SIZE || 820),
    show_lines: process.env.LINES !== "0",
    title: process.env.TITLE || ""
};

const target = document.getElementById("figure");
viewer.render(target, data, config, d3);

const svg = target.querySelector("svg");
if (!svg) {
    throw new Error("render produced no svg");
}
// A figure in a document does not need a viewBox-sized box; keep it flexible.
svg.setAttribute("width", String(config.size));
svg.removeAttribute("role");
svg.setAttribute("role", "img");
svg.setAttribute("aria-label", config.title || "surface");

fs.writeFileSync(outPath, svg.outerHTML, "utf8");

const legend = target.querySelector(".surfit-legend");
process.stdout.write(JSON.stringify({
    file: outPath,
    bytes: fs.statSync(outPath).size,
    legend: legend ? legend.textContent : null
}));
