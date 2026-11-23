"use client";

import { createChart, ColorType, CrosshairMode, CandlestickSeries, LineSeries } from "lightweight-charts";
import { useEffect, useRef } from "react";

const MA_COLORS: Record<number, string> = {
  20: "#C08A2E",
  50: "#0E8A5F",
  100: "#2F7EA8",
  200: "#8CA096",
};

const EMPTY_MAS: number[] = [];

export default function Chart({
  series,
  mas = EMPTY_MAS,
  height = 400,
}: {
  series: any[];
  mas?: number[];
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !series.length) return;
    const container = ref.current;
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#6C8377",
        fontFamily: "Inter, system-ui, sans-serif",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(16, 64, 43, 0.06)" },
        horzLines: { color: "rgba(16, 64, 43, 0.06)" },
      },
      rightPriceScale: {
        borderColor: "rgba(16, 64, 43, 0.10)",
        scaleMargins: { top: 0.12, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "rgba(16, 64, 43, 0.10)",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 3,
        barSpacing: 7,
      },
      width: container.clientWidth,
      height,
      autoSize: true,
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: "rgba(14, 138, 95, 0.45)",
          width: 1,
          style: 2,
          labelBackgroundColor: "#0A5C41",
        },
        horzLine: {
          color: "rgba(14, 138, 95, 0.45)",
          width: 1,
          style: 2,
          labelBackgroundColor: "#0A5C41",
        },
      },
    } as any);

    const data = series.map((s: any) => ({
      time: s.date,
      open: s.open,
      high: s.high,
      low: s.low,
      close: s.close,
    }));

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#0E9F6E",
      downColor: "#D14343",
      borderDownColor: "#D14343",
      borderUpColor: "#0E9F6E",
      wickDownColor: "#D14343",
      wickUpColor: "#0E9F6E",
      borderVisible: false,
      borderWidth: 0,
      wickVisible: true,
      priceLineColor: "rgba(14, 138, 95, 0.5)",
      priceLineStyle: 2,
    } as any);
    candle.setData(data);

    for (const n of mas) {
      if (n >= series.length) continue;
      const values: any[] = [];
      let acc = 0;
      for (let i = 0; i < series.length; i++) {
        acc += series[i].close;
        if (i >= n) acc -= series[i - n].close;
        if (i >= n - 1) values.push({ time: series[i].date, value: acc / n });
      }
      const line = chart.addSeries(LineSeries, {
        color: MA_COLORS[n] || "#0E8A5F",
        lineWidth: 2,
        lastValueVisible: false,
        priceLineVisible: false,
        crosshairMarkerRadius: 3,
      } as any);
      line.setData(values);
    }

    const visible = Math.min(120, data.length);
    chart.timeScale().setVisibleLogicalRange({
      from: Math.max(0, data.length - visible),
      to: data.length + 2,
    });

    const resize = () => chart.applyOptions({ width: container.clientWidth });
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
    };
  }, [series, mas, height]);

  if (!series.length) {
    return (
      <div
        className="mt-4 flex w-full items-center justify-center rounded-2xl border border-dashed border-line bg-white/40 text-sm text-fg-muted"
        style={{ height }}
      >
        Price history is loading…
      </div>
    );
  }

  return (
    <div className="chart-shell mt-4 w-full" style={{ height }}>
      <div ref={ref} className="h-full w-full" />
    </div>
  );
}
