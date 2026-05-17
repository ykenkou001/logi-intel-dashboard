"use client";

/**
 * クライアントサイド計測コンポーネント。
 *
 * - ルート遷移ごとに `page_view` イベントを送る（Next.js App Router の SPA 遷移対応）
 * - タブが非表示・離脱する瞬間に「実際に見ていた時間」を `engagement_time_msec`
 *   として送る（GA4 のエンゲージメント時間の定義に合わせる）
 * - 同一 origin の `/api/v1/analytics/collect` に POST するため
 *   アドブロッカーで弾かれにくい
 * - ブラウザ単位の永続 ID は `localStorage` の UUID v4 で持つ（Cookie 不使用）
 */

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

const STORAGE_KEY = "logi-intel-client-id";
const SESSION_KEY = "logi-intel-session-id";
const COLLECT_ENDPOINT =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "") + "/api/v1/analytics/collect";

type EventParams = {
  page_location?: string;
  page_title?: string;
  page_referrer?: string;
  engagement_time_msec?: number;
  session_id?: string;
};

function getOrCreateClientId(): string {
  if (typeof window === "undefined") return "";
  let id = window.localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = window.sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = String(Date.now());
    window.sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

function send(eventName: string, params: EventParams, useBeacon: boolean): void {
  const clientId = getOrCreateClientId();
  if (!clientId) return;
  // GA4 Measurement Protocol は session_id と engagement_time_msec が両方無いと
  // engaged session として認識せずリアルタイム/標準レポートから除外する。
  // gtag.js は internal で常時付与する挙動なので、手動実装でも常時付与する。
  const enrichedParams: EventParams = {
    ...params,
    session_id: params.session_id ?? getOrCreateSessionId(),
    engagement_time_msec: params.engagement_time_msec ?? 1,
  };
  const body = JSON.stringify({
    client_id: clientId,
    events: [{ name: eventName, params: enrichedParams }],
  });
  // 離脱イベントは fetch では送信が間に合わないため Beacon を使う
  if (useBeacon && typeof navigator !== "undefined" && "sendBeacon" in navigator) {
    const blob = new Blob([body], { type: "application/json" });
    navigator.sendBeacon(COLLECT_ENDPOINT, blob);
    return;
  }
  void fetch(COLLECT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {
    // 計測失敗はアプリの動作に影響させない
  });
}

export function Analytics(): null {
  const pathname = usePathname();
  // 「実際にアクティブだった時間」を engagement_time_msec として計測するため
  // ページ表示開始時刻を ref で保持し、離脱／非表示時に diff を取る
  const activeSinceRef = useRef<number>(Date.now());
  const lastPathRef = useRef<string | null>(null);

  useEffect(() => {
    if (!pathname) return;

    // 前のページの滞在時間を送ってから、新ページの page_view を送る
    const now = Date.now();
    if (lastPathRef.current && lastPathRef.current !== pathname) {
      const engagement = now - activeSinceRef.current;
      send(
        "user_engagement",
        { engagement_time_msec: Math.min(engagement, 30 * 60 * 1000) },
        false,
      );
    }
    activeSinceRef.current = now;
    lastPathRef.current = pathname;

    send(
      "page_view",
      {
        page_location: window.location.origin + pathname,
        page_title: document.title,
        page_referrer: document.referrer || undefined,
        session_id: getOrCreateSessionId(),
      },
      false,
    );
  }, [pathname]);

  useEffect(() => {
    // タブ非表示・ページ離脱の瞬間にエンゲージメント時間を Beacon で送る
    function flush(useBeacon: boolean): void {
      const engagement = Date.now() - activeSinceRef.current;
      if (engagement <= 0) return;
      send(
        "user_engagement",
        { engagement_time_msec: Math.min(engagement, 30 * 60 * 1000) },
        useBeacon,
      );
      activeSinceRef.current = Date.now();
    }
    function onVisibility(): void {
      if (document.visibilityState === "hidden") {
        flush(true);
      } else {
        activeSinceRef.current = Date.now();
      }
    }
    function onPageHide(): void {
      flush(true);
    }
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", onPageHide);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", onPageHide);
    };
  }, []);

  return null;
}
