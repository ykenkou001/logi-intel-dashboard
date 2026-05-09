"""静的データレジストリの初期化。

各 static モジュールを import するだけで `_freshness.register()` が走り、
鮮度メタデータがレジストリに登録される。利用側は `import core.static` 1 行で
全モジュールを有効化できる。
"""

from __future__ import annotations

# 副作用 import: 各モジュールロード時に _freshness.register() が走る
from core.static import (  # noqa: F401
    co2_factors,
    efficiency_law_certified,
    improvement_standards,
    industry_freight_coef,
    jsic,
    national_targets,
)
