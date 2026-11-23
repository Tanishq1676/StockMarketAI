"use client";

import { useEffect, useRef, useState } from "react";
import { WS_URL } from "@/lib/api";

type Row = {
  symbol: string;
  name?: string;
  price?: number;
  change_pct?: number;
  volume?: number;
  prev_close?: number | null;
  trade_date?: string | null;
  last_updated?: string;
  data_source?: string;
  is_live?: boolean;
  delay_minutes?: number;
};

const mapRow = (r: Row) => ({
  symbol: r.symbol,
  name: r.name,
  price: r.price,
  change_pct: r.change_pct,
  volume: r.volume,
  prev_close: r.prev_close,
  trade_date: r.trade_date,
  last_updated: r.last_updated,
  data_source: r.data_source,
  is_live: r.is_live,
  delay_minutes: r.delay_minutes,
});

export default function useLiveUpdates() {
  const [live, setLive] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    const timer = setTimeout(() => {
      if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
        // do nothing on timeout; the ws closes if backend absent
      }
    }, 5000);
    ws.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        setLive({
          updatedAt: payload.timestamp,
          indices: payload.indices?.map(mapRow),
          top_gainers: payload.top_gainers?.map(mapRow),
          top_losers: payload.top_losers?.map(mapRow),
          most_active: payload.most_active?.map(mapRow),
          unusual_volume: payload.unusual_volume?.map(mapRow),
          summary: "Live market feed connected",
        });
      } catch {
        /* ignore bad payloads */
      }
    };
    ws.onopen = () => {
      console.info("ws connected");
      setLive((l: any) => ({ ...l, summary: "Live market feed connected" }));
    };
    ws.onclose = () => setLive((l: any) => ({ ...l, summary: "Live market feed disconnected; refreshing…" }));
    ws.onerror = () => {
      /* backend may be down; polling will cover */
    };
    return () => {
      clearTimeout(timer);
      ws.close();
    };
  }, []);

  return { live };
}
