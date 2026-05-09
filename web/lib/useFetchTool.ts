"use client";

import { useState, useCallback } from "react";

/**
 * 各ダッシュボードページに散在していた fetch + loading + error の三点セットを
 * 共通化するフック。
 *
 * 使い方:
 *   const { data, loading, error, run } = useFetchTool<ToolResponse>();
 *   await run(() => fetchBenchmark(args));
 */
export function useFetchTool<T>() {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (fetcher: () => Promise<T>): Promise<T | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
      return result;
    } catch (e) {
      const message = e instanceof Error ? e.message : "通信エラー";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, loading, error, run, reset };
}
