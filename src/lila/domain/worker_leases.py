"""Renew only currently valid leases belonging to the authenticated worker."""
from lila.domain.core import DomainError
from lila.security.sessions import timestamp


def renew(domain,worker):
    def change(db):
        domain.check_time()
        rows=db.execute('SELECT l.id,l.run_id,l.generation,r.state,r.stop_requested FROM leases l JOIN runs r ON r.id=l.run_id WHERE l.worker_id=? AND l.fenced=0',(worker,)).fetchall()
        for lease,run,generation,state,stopped in rows:
            if state in {'STOPPED','COMPLETED'} or stopped:
                db.execute('UPDATE leases SET fenced=1 WHERE id=?',(lease,))
                continue
            try:
                domain._lease(db,lease,worker,generation,run,require_live=False)
            except DomainError as exc:
                if exc.code!='STALE_LEASE':
                    raise
                db.execute('UPDATE leases SET fenced=1 WHERE id=?',(lease,))
                continue
            db.execute('UPDATE leases SET expires_at=? WHERE id=?',(timestamp(domain.clock()+10),lease))
            domain.lease_deadlines[lease]=domain.monotonic()+10
    with domain.dispatch_lock:
        domain.writer.call(change)
