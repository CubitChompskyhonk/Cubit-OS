"""Optional commerce layer. Disabled by default — free core never requires it."""
from .stripe_wallet import CommerceGateway

__all__ = ["CommerceGateway"]
