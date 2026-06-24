"""Publishing layer.

Abstracts where approved content goes. Defaults to a safe **dry-run** publisher so
the platform is fully operational offline (nothing is posted, everything is logged);
configure ``POSTIZ_API_URL`` + ``POSTIZ_API_KEY`` to publish for real via Postiz.
"""

from invisable_os.publish.base import Publisher, PublishResult
from invisable_os.publish.factory import get_publisher

__all__ = ["Publisher", "PublishResult", "get_publisher"]
