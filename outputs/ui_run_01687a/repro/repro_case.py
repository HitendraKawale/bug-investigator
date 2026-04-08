from pathlib import Path
import sys

REPO_ROOT = Path(r"/Users/hitesh/bug-investigator/inputs/mini_repo").resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cache import CACHE
from service import get_user_tier

CACHE.clear()

if __name__ == "__main__":
    print(get_user_tier("new_user_123"))
