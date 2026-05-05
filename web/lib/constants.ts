export const PREFECTURES = [
  "北海道",
  "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
  "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
  "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
  "岐阜県", "静岡県", "愛知県", "三重県",
  "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
  "鳥取県", "島根県", "岡山県", "広島県", "山口県",
  "徳島県", "香川県", "愛媛県", "高知県",
  "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
] as const;

export const JSIC_PRESETS = [
  { code: "5411", label: "5411 食料・飲料卸売業" },
  { code: "5611", label: "5611 各種商品小売業" },
  { code: "5811", label: "5811 食料・飲料小売業" },
  { code: "4411", label: "4411 一般貨物自動車運送業" },
  { code: "1631", label: "1631 医薬品製造業" },
  { code: "2911", label: "2911 電子部品製造業" },
] as const;

export const FORM3_SECTIONS = [
  { value: "load", label: "load（積載）" },
  { value: "wait", label: "wait（荷待ち）" },
  { value: "loading", label: "loading（荷役等）" },
] as const;

export const MEASURE_TYPES = [
  { value: "modal_shift", label: "modal_shift（モーダルシフト）" },
  { value: "load_factor", label: "load_factor（積載率）" },
  { value: "joint_delivery", label: "joint_delivery（共同配送）" },
  { value: "relay_transport", label: "relay_transport（中継輸送）" },
  { value: "berth_booking", label: "berth_booking（バース予約）" },
  { value: "warehouse_dx", label: "warehouse_dx（倉庫 DX）" },
] as const;

export const INDUSTRY_CATEGORIES = [
  { value: "manufacturing", label: "manufacturing（製造業）" },
  { value: "wholesale", label: "wholesale（卸売業）" },
  { value: "retail", label: "retail（小売業）" },
  { value: "chain_franchise", label: "chain_franchise（連鎖化）" },
  { value: "transport", label: "transport（運輸業）" },
  { value: "other", label: "other（その他）" },
] as const;
