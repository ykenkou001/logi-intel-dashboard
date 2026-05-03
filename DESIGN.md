---
version: alpha
name: Logi-Intel CLO Report
description: CLO中長期計画書ドラフト用ビジュアルアイデンティティ

colors:
  primary: "#1E2761"
  primary-dk: "#141A45"
  secondary: "#CADCFC"
  surface: "#EAF1FE"
  on-primary: "#FFFFFF"
  muted: "#5B6478"
  border: "#B8C0CE"
  accent: "#F5B82E"
  positive: "#2DD4BF"
  negative: "#EF6F6C"

typography:
  h1: { fontFamily: "Yu Gothic UI", fontSize: 54px, fontWeight: 700 }
  h2: { fontFamily: "Yu Gothic UI", fontSize: 30px, fontWeight: 700 }
  kpi-xl: { fontFamily: "Yu Gothic UI", fontSize: 56px, fontWeight: 700 }
  kpi-lg: { fontFamily: "Yu Gothic UI", fontSize: 44px, fontWeight: 700 }
  body: { fontFamily: "Yu Gothic UI", fontSize: 12px, fontWeight: 400 }
  caption: { fontFamily: "Yu Gothic UI", fontSize: 10px, fontWeight: 400 }
  eyebrow: { fontFamily: "Yu Gothic UI", fontSize: 11px, fontWeight: 700, letterSpacing: 0.04em }

spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px

components:
  kpi-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    padding: 16px
  kpi-card-accent:
    backgroundColor: "{colors.accent}"
    width: 6px
  alert-banner:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.negative}"
  hero-card:
    backgroundColor: "{colors.primary-dk}"
    textColor: "{colors.on-primary}"

x-pptx:
  layout: LAYOUT_WIDE
  slide-templates:
    - title
    - kpi-dashboard
    - benchmark
    - alert-stat
    - verdict
    - target-grid-2x2
    - data-table
    - ranked-list
    - appendix
---

# Overview

物流効率化法 第46条／第65条 対応の法定報告書を、エグゼクティブが
3分で意思決定できるダッシュボード形式で表現する。基調はネイビー +
アンバーアクセント。データを大型数値で前面に押し出す。

## Colors

- **Primary (#1E2761):** 信頼感の中核。タイトル・本文・濃色面。
- **Accent (#F5B82E):** KPI・章番号・警告のみに使用。多用しない。
- **Positive/Negative:** CO2削減等は teal、不足・罰金等は coral。

## Typography

日本語主体のため Yu Gothic UI を全面採用。KPI数値のみ 44px+ で
パンチを出す。本文は 12px、出典は 10px に統一。

## Layout

16:9 ワイド (13.3"x7.5")。マージンは左右 0.5"、上下 0.4"。
カード間隔は 0.15-0.2"。各スライドに「番号 + 英文セクションラベル」
の eyebrow を付与し、章のリズムを作る。

## Do's and Don'ts

- KPI は大型数値 + 小ラベルの組合せ
- 出典はスライド下端に薄字で
- ベタ塗りの帯や AI スライド風の下線は使わない
- 全カラー均等配置は避け、navy 60-70% を死守
