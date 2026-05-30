# =====================
# Settings
# =====================
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# =====================
# Imports
# =====================
import 'quality.just'

# Local commands (do not commit)
import? 'local.just'
