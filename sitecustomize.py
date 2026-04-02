from __future__ import annotations

import os
if os.getenv("MOIRA_PYTEST_PLUGIN_AUTOLOAD", "0") != "1":
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
