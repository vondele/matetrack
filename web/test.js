// smoke test for the interactive graphs: parses the csv files, checks the
// commit subject coverage, server-side renders all charts in both views and
// both themes, exercises the tooltip formatters, and checks the zoom handling
// that the live stats are based on. Run with 'node test.js' from the web/
// directory (or any other directory), it finds the data in web/data or in
// the repo root.

"use strict";

var fs = require("fs");
var path = require("path");

var echarts = require("./echarts.min.js");
var m = require("./app.js");

var dataDir = fs.existsSync(path.join(__dirname, "data"))
  ? path.join(__dirname, "data")
  : path.join(__dirname, "..");
var subjects = JSON.parse(
  fs.readFileSync(path.join(dataDir, "commitsubjects.json"), "utf8")
);

var failures = 0;
var leftSeen = false; // whether the stats moved to the bottom left side
var rightSeen = false; // whether the stats moved to the bottom right side
function check(cond, msg) {
  if (cond) {
    console.log("ok: " + msg);
  } else {
    failures++;
    console.error("FAIL: " + msg);
  }
}

check(
  m.THEMES.dark.axis !== m.THEMES.light.axis &&
    m.THEMES.dark.mates !== m.THEMES.light.mates,
  "dark theme palette differs from light"
);
var probeLight = m.buildOptions(m.SUITES[0], m.parseCSV(
  fs.readFileSync(path.join(dataDir, m.SUITES[0].file), "utf8")
), {}, "chronological");
m.setTheme("dark");
var probeDark = m.buildOptions(m.SUITES[0], m.parseCSV(
  fs.readFileSync(path.join(dataDir, m.SUITES[0].file), "utf8")
), {}, "chronological");
check(
  probeLight.tooltip.backgroundColor === m.THEMES.light.tooltipBg &&
    probeDark.tooltip.backgroundColor === m.THEMES.dark.tooltipBg &&
    probeDark.series[0].itemStyle.color === m.THEMES.dark.mates,
  "setTheme switches the chart palette"
);

["light", "dark"].forEach(function (theme) {
  m.setTheme(theme);
  var pal = m.THEMES[theme];
  console.log("theme: " + theme);

m.SUITES.forEach(function (suite) {
  var rows = m.parseCSV(
    fs.readFileSync(path.join(dataDir, suite.file), "utf8")
  );
  var n = rows.length;
  check(rows.length > 4000, suite.file + ": parsed " + rows.length + " rows");

  var missing = rows.filter(function (r) { return !subjects[r.sha]; });
  check(
    missing.length === 0,
    suite.file + ": " + (rows.length - missing.length) + "/" + rows.length +
      " SHAs have a commit subject"
  );

  var withStats = rows.filter(function (r) { return r.mates !== null; });
  check(withStats.length > 1000, suite.file + ": " + withStats.length + " rows with stats");

  m.VIEWS.forEach(function (view) {
    var options = m.buildOptions(suite, rows, subjects, view);
    var yAxes = Array.isArray(options.yAxis) ? options.yAxis : [options.yAxis];
    var wantNames = view === "chronological"
      ? { y: ["mates"], x: "date" }
      : { y: ["best mates", "mates"], x: "commit counter" };
    check(
      yAxes.map(function (y) { return y.name; }).join() === wantNames.y.join() &&
        yAxes.every(function (y) {
          return y.nameLocation === "middle" && y.nameRotate === 90 && y.nameGap === 52;
        }) &&
        options.xAxis.name === wantNames.x &&
        options.xAxis.nameLocation === "middle" &&
        options.grid.left === 64 &&
        options.grid.right === (view === "chronological" ? 24 : 70),
      suite.key + "/" + view + ": x and y axis names set, names clear of tick labels"
    );
    check(
      options.series[0].markLine.label.color === options.xAxis.axisLabel.color &&
        options.series[0].markLine.label.fontWeight === "bold" &&
        options.series[0].markLine.label.fontSize === 10,
      suite.key + "/" + view + ": tag labels match x-axis label color, bold"
    );
    check(
      yAxes.every(function (y) { return y.scale === true; }) &&
        options.series
          .filter(function (s) { return s.name === "mates" || s.name === "best mates"; })
          .every(function (s) { return s.symbolSize === 6; }),
      suite.key + "/" + view + ": y-axes scale to data, dot size 6"
    );
    var issueSeries = options.series.filter(function (s) {
      return s.name === "needs investigation" || s.name === "needed investigation";
    });
    check(
      issueSeries.length === 0 ||
        (issueSeries[0].symbolSize === 10 &&
          issueSeries[0].itemStyle.color === "rgba(0,0,0,0)" &&
          issueSeries[0].itemStyle.borderWidth > 0),
      suite.key + "/" + view + ": issue markers are hollow rings"
    );
    check(
      options.title.text.indexOf(suite.label) !== -1 &&
        options.title.textStyle.fontSize === 13 &&
        options.title.textStyle.fontWeight === "bold" &&
        options.title.textStyle.color === pal.text,
      suite.key + "/" + view + ": bold graph title with suite label in theme color"
    );
    check(
      options.legend &&
        options.grid.show === true &&
        options.legend.textStyle.color === pal.text &&
        options.tooltip.backgroundColor === pal.tooltipBg &&
        options.tooltip.textStyle.color === pal.text,
      suite.key + "/" + view + ": legend, tooltip and grid box themed"
    );
    check(
      yAxes.every(function (y) { return y.axisLabel.fontSize === 12; }) &&
        options.xAxis.axisLabel.fontSize === 12,
      suite.key + "/" + view + ": uniform axis label font size 12"
    );
    check(
      options.dataZoom[1].left === "19%" && options.dataZoom[1].right === "19%" &&
        options.dataZoom[1].height === 44 &&
        options.dataZoom[1].dataBackground.lineStyle.color === pal.sliderData,
      suite.key + "/" + view + ": golden ratio slider with visible data preview"
    );
    if (view === "commits") {
      check(
        options.dataZoom[0].startValue === 1 - Math.min(50, n) &&
          options.dataZoom[0].endValue === 0 &&
          options.xAxis.min === 1 - n &&
          options.xAxis.max === 0,
        suite.key + "/" + view + ": axis 1-N..0, default zoom last 50"
      );
    } else {
      check(
        options.dataZoom[0].startValue === undefined &&
          options.dataZoom[0].start === undefined,
        suite.key + "/" + view + ": default zoom full range"
      );
    }

    var chart = echarts.init(null, null, {
      renderer: "svg",
      ssr: true,
      width: 950,
      height: 460
    });
    chart.setOption(options);
    // draw the stats inside the grid, as renderAll's updateStats does
    var span0 = m.visibleSpan(chart, rows, view);
    var lines0 = m.statsLines(rows, span0.from, span0.to);
    var side0 = m.statsSide(chart, rows, view, span0, m.measureTextWidth(lines0));
    var rightMargin = view === "chronological" ? 24 : 70;
    chart.setOption(m.statsGraphic(lines0, side0, rightMargin));
    var svg = chart.renderToSVGString();

    check(
      (side0 === "left" || side0 === "right") &&
        svg.indexOf("best mates \u2282") !== -1 &&
        svg.indexOf("mates \u2282") !== -1,
      suite.key + "/" + view + ": stats drawn at the bottom, " + side0 + " side"
    );
    // independent recount via convertToPixel: the chosen side must have no
    // more points inside the stats text rectangle than the other side
    var recount = { left: 0, right: 0 };
    var gridB2 = 460 - 96;
    var gridL2 = 64;
    var gridR2 = 950 - (view === "chronological" ? 24 : 70);
    var textW2 = m.measureTextWidth(lines0);
    [["mates", 0], ["bmates", 1]].forEach(function (s) {
      for (var ri = span0.from; ri <= span0.to; ri++) {
        var rv = rows[ri][s[0]];
        if (rv === null) continue;
        var rx = view === "chronological" ? rows[ri].date : ri - rows.length + 1;
        var rp = chart.convertToPixel({ seriesIndex: s[1] }, [rx, rv]);
        if (rp[1] < gridB2 - 44 || rp[1] > gridB2 - 4) continue;
        if (rp[0] >= gridL2 + 4 && rp[0] <= gridL2 + 12 + textW2) recount.left++;
        else if (rp[0] >= gridR2 - 12 - textW2 && rp[0] <= gridR2 - 4) recount.right++;
      }
    });
    check(
      (side0 === "left" && recount.left <= recount.right) ||
        (side0 === "right" && recount.right <= recount.left),
      suite.key + "/" + view + ": stats side has minimal overlap " +
        "(left " + recount.left + " vs right " + recount.right + ", chose " + side0 + ")"
    );
    // y-axis tick labels are integers and follow the tick interval, so the
    // topmost label is in the normal sequence (checked per axis by its color)
    var axisFills = view === "chronological"
      ? [pal.label]
      : [pal.bmates, pal.matesLabel];
    function tickSequenceOk() {
      return axisFills.every(function (fill) {
        var nums = [...svg.matchAll(/<text ([^>]*)>([0-9][0-9.,]*)</g)]
          .filter(function (t) {
            if (t[1].indexOf('fill="' + fill + '"') === -1) return false;
            var anchor = (t[1].match(/text-anchor="(\w+)"/) || [])[1];
            if (anchor === "middle") return false; // x-axis labels
            var tr = t[1].match(/translate\(([\d.]+) /);
            return tr && (+tr[1] < 100 || +tr[1] > 850); // y-axis labels only
          })
          .map(function (t) { return +t[2].replace(/,/g, ""); });
        if (nums.length < 2) return false;
        var interval = nums[1] - nums[0];
        return (
          Number.isInteger(interval) &&
          interval > 0 &&
          nums.every(function (v) { return Number.isInteger(v) && v % interval === 0; })
        );
      });
    }
    check(
      tickSequenceOk(),
      suite.key + "/" + view + ": y-axis ticks are integers in sequence"
    );
    if (side0 === "left") leftSeen = true;
    else rightSeen = true;
    if (view === "chronological") {
      check(
        side0 === (suite.key === "matetrack" ? "right" : "left"),
        suite.key + "/" + view + ": stats side for the full range is " + side0 +
          " (matetrack's early low data crowds the bottom left, classic's " +
          "recent best mates run along the bottom right)"
      );
    }
    // the stats text sits at the bottom inside the grid, on the chosen side
    var statsPos = null;
    [...svg.matchAll(/<text ([^>]*)>([^<]*\u2282[^<]*)</g)].forEach(function (t) {
      var tr = t[1].match(/translate\(([\d.]+) ([\d.]+)\)/);
      var ya = t[1].match(/y="([\d.]+)"/);
      var xa = t[1].match(/x="(-?[\d.]+)"/);
      var pos = {
        x: tr ? +tr[1] : xa ? +xa[1] : null,
        y: tr ? +tr[2] : ya ? +ya[1] : null
      };
      if (pos.x !== null && (statsPos === null || pos.y < statsPos.y)) statsPos = pos;
    });
    check(
      statsPos !== null &&
        statsPos.y > 460 - 96 - 60 &&
        statsPos.y < 460 - 96 &&
        (side0 === "left" ? statsPos.x <= 64 + 9 : statsPos.x > 400),
      suite.key + "/" + view + ": stats text at the bottom " + side0 +
        " (x=" + (statsPos && Math.round(statsPos.x)) + ", y=" + (statsPos && Math.round(statsPos.y)) + ")"
    );

    // y-axis headroom via boundaryGap: top data points clear the tag label
    // zone and GOAT pins stay inside the grid, while ECharts keeps full
    // control of the tick sequence
    check(
      yAxes.every(function (y) {
        return Array.isArray(y.boundaryGap) && y.boundaryGap.join() === "0%,25%";
      }),
      suite.key + "/" + view + ": y-axis has top boundary gap headroom"
    );
    function topClearsTagZone(from, to) {
      return ["mates", "bmates"].every(function (key, si) {
        var max = -Infinity;
        for (var i = from; i <= to; i++) {
          if (rows[i][key] !== null && rows[i][key] > max) max = rows[i][key];
        }
        var py = chart.convertToPixel({ seriesIndex: si }, [0, max])[1];
        return py >= 105; // grid top 60 + tag label zone ~43 + margin
      });
    }
    check(
      topClearsTagZone(span0.from, span0.to),
      suite.key + "/" + view + ": visible data clears the tag label zone"
    );
    var goatY = [...svg.matchAll(/<text ([^>]*)>GOAT</g)]
      .map(function (g) {
        var tr = g[1].match(/translate\(([\d.]+) ([\d.]+)\)/);
        return tr ? +tr[2] : null;
      })
      .filter(function (y) { return y !== null; });
    check(
      goatY.length === 0 || goatY.every(function (y) { return y > 60; }),
      suite.key + "/" + view + ": GOAT pins inside the grid" +
        (goatY.length ? " (y=" + goatY.map(Math.round).join(", ") + ")" : "")
    );

    var goatInView =
      view === "chronological" ||
      ["mates", "bmates"].some(function (key) {
        return m.goat(rows, key).idx >= n - 50;
      });
    check(svg.indexOf("<svg") === 0 && svg.length > 5000,
      suite.key + "/" + view + ": SSR rendered " + svg.length + " bytes");
    check(svg.indexOf('stroke="' + pal.axis + '"') !== -1,
      suite.key + "/" + view + ": grid border rendered in theme color");
    check(
      svg.indexOf(">" + wantNames.x + "<") !== -1 &&
        yAxes.every(function (y) { return svg.indexOf(">" + y.name + "<") !== -1; }),
      suite.key + "/" + view + ": axis names rendered"
    );
    if (view === "commits") {
      var nameX = [];
      [...svg.matchAll(/<text ([^>]*matrix[^>]*)>(?:<tspan[^>]*>)?(best mates|mates)</g)]
        .forEach(function (t) {
          var mm = t[1].match(/matrix\(0,-1,1,0,([\d.]+),/);
          if (mm) nameX.push(+mm[1]);
        });
      check(
        nameX.length === 2 && Math.abs(nameX[0] - nameX[1]) > 100,
        suite.key + "/" + view + ": y-axis names at distinct positions " +
          "(" + nameX.join(", ") + ")"
      );
    }
    check(svg.indexOf("GOAT") !== -1 === goatInView,
      suite.key + "/" + view + ": GOAT label " +
        (goatInView ? "present" : "absent, GOAT outside default window"));

    // default and full zoom spans, as used for the live stats line
    var def = m.visibleSpan(chart, rows, view);
    chart.dispatchAction({ type: "dataZoom", start: 0, end: 100 });
    var full = m.visibleSpan(chart, rows, view);
    check(
      topClearsTagZone(full.from, full.to),
      suite.key + "/" + view + ": full zoom data clears the tag label zone"
    );
    var issueRows = rows.filter(function (r) { return r.issues; }).length;
    if (view === "commits" && issueRows) {
      var rings = (chart.renderToSVGString().match(
        /ecmeta_series_index="2"[^>]*ecmeta_ssr_type="chart"/g) || []).length;
      check(
        rings === issueRows,
        suite.key + "/" + view + ": all " + issueRows + " issue rings rendered"
      );
    }
    // sample zoom windows to exercise the side choice for the stats text and,
    // less frequently, the y-axis tick sequences
    for (var zs = 0; zs <= 95; zs += 5) {
      chart.dispatchAction({ type: "dataZoom", start: zs, end: Math.min(zs + 5, 100) });
      var spanZ = m.visibleSpan(chart, rows, view);
      var linesZ = m.statsLines(rows, spanZ.from, spanZ.to);
      var sideZ = m.statsSide(chart, rows, view, spanZ, m.measureTextWidth(linesZ));
      if (sideZ === "left") leftSeen = true;
      else if (sideZ === "right") rightSeen = true;
      check(
        sideZ === "left" || sideZ === "right",
        suite.key + "/" + view + ": valid stats side for window " + zs + ".." + (zs + 5) + "%"
      );
      if (zs % 15 === 0) {
        svg = chart.renderToSVGString();
        check(
          tickSequenceOk(),
          suite.key + "/" + view + ": y-axis ticks in sequence for window " + zs + ".." + (zs + 5) + "%"
        );
      }
    }
    chart.dispose();
    check(
      full.from === 0 && full.to === n - 1,
      suite.key + "/" + view + ": full zoom shows all " + n + " rows"
    );
    var wantDefault = view === "chronological"
      ? { from: 0, to: n - 1 }
      : { from: n - 50, to: n - 1 };
    check(
      def.from === wantDefault.from && def.to === wantDefault.to,
      suite.key + "/" + view + ": default zoom shows rows " +
        def.from + ".." + def.to + " (want " + wantDefault.from + ".." + wantDefault.to + ")"
    );

    var html = options.tooltip.formatter([
      { seriesName: "mates", dataIndex: 100 }
    ]);
    check(
      html.indexOf("official-stockfish/Stockfish/commit/" + rows[100].sha) !== -1 &&
        html.indexOf(rows[100].sha.slice(0, 7)) !== -1,
      suite.key + "/" + view + ": tooltip links the Stockfish commit"
    );
    check(
      html.indexOf(escHtml(subjects[rows[100].sha])) !== -1,
      suite.key + "/" + view + ": tooltip shows the commit subject"
    );
  });

  var last = n - 1;
  check(
    m.nearestRow(rows, "chronological", rows[0].date) === 0 &&
      m.nearestRow(rows, "chronological", rows[last].date) === last &&
      m.nearestRow(rows, "chronological", rows[last].date + 1e9) === last,
    suite.file + ": nearestRow finds first/last row for chronological view"
  );
  check(
    m.nearestRow(rows, "commits", 0) === last &&
      m.nearestRow(rows, "commits", -49) === last - 49 &&
      m.nearestRow(rows, "commits", 1 - n) === 0 &&
      m.nearestRow(rows, "commits", 1e6) === last &&
      m.nearestRow(rows, "commits", -1e6) === 0,
    suite.file + ": nearestRow maps commits ago to rows"
  );
  check(
    m.statsLines(rows, 0, last)[0].text.indexOf("\u2282") !== -1 &&
      m.statsLines(rows, 0, last)[0].text !== m.statsLines(rows, last - 49, last)[0].text,
    suite.file + ": stats over full range differ from last 50"
  );

  ["mates", "bmates"].forEach(function (key) {
    var g = m.goat(rows, key);
    console.log(
      "info: " + suite.key + " GOAT " + key + ": " + g.value +
        " on " + new Date(rows[g.idx].date).toISOString().slice(0, 10)
    );
  });
});

}); // theme loop

check(
  leftSeen && rightSeen,
  "stats side selection jumps between left and right over the zoom windows"
);

function escHtml(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

process.exit(failures ? 1 : 0);
