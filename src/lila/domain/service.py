from .core import Core
from .tasks import Tasks
from .facts import Facts
from .identity import Identity
from .policies import Policies
from .ledger import Ledger
from .reads import Reads
from .lifecycle import Lifecycle
from .corrections import Corrections
from .criteria import Criteria


class Domain(Tasks, Facts, Identity, Policies, Ledger, Reads, Lifecycle, Corrections, Criteria, Core):
    """Single-writer domain; adapters must authenticate before calling internal methods."""
