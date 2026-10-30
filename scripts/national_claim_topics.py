# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "mlx==0.32.4",
#     "mlx-vlm==0.3.12",
#     "mlx-lm==0.30.7",
#     "transformers==5.1.0",
# ]
# ///
"""Generate topic summaries in the existing isolated local MLX environment."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dsa_analysis.national_claim_topics import main  # noqa: E402

if __name__ == "__main__":
    main()
