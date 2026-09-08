from uuid import uuid4
from lila.domain.core import DomainError,validate,identifier,GLOBAL_ID

TERMINAL = {"STOPPED","COMPLETED"}


class Tasks:
    def create_task(self,principal,body):
        body = validate("CreateTask",body)
        def change(db):
            self.account(db,body["account_id"])
            entity = str(uuid4())
            instruction = self.content(db,"instruction",body["instruction"])
            criteria = self.content(db,"criteria",body["criteria"])
            db.execute("INSERT INTO tasks VALUES(?,?,?,?,1,?)",(entity,body["account_id"],instruction,criteria,self.stamp()))
            self.event(db,"TASK_CREATED","task",entity,1)
            return self.receipt(entity,1,"DRAFT")
        return self.command(principal,body["command_id"],["create_task",body],change)

    def _task(self,db,task_id):
        row = db.execute("SELECT account_id,revision FROM tasks WHERE id=?",(identifier(task_id),)).fetchone()
        if not row:
            raise DomainError("NOT_FOUND",404)
        return row

    def _run(self,db,task_id):
        return db.execute("SELECT id,state,individual_hold,generation,revision FROM runs WHERE task_id=? ORDER BY generation DESC LIMIT 1",(task_id,)).fetchone()

    def _snapshot(self,db,task_id):
        task = self._task(db,task_id)
        run = self._run(db,task_id)
        global_hold = bool(db.execute("SELECT global_hold FROM execution_control WHERE id=1").fetchone()[0])
        reasons = []
        state = "DRAFT" if not run else run[1]
        if run and state not in TERMINAL:
            reasons.extend(self.readiness())
            reasons.extend(r[0] for r in db.execute('SELECT reason FROM run_blockers WHERE run_id=? ORDER BY reason',(run[0],)))
            if global_hold:
                reasons.append("GLOBAL_HOLD")
            if run[2]:
                reasons.append("INDIVIDUAL_HOLD")
            if db.execute("SELECT 1 FROM actions a JOIN runs r ON r.id=a.run_id WHERE r.task_id=? AND a.state IN('CLAIMED','DISPATCHED','UNCERTAIN') LIMIT 1",(task_id,)).fetchone():
                reasons.append("OUTCOME_UNRESOLVED")
            if run[2] or global_hold:
                state = "PAUSED"
            elif reasons and state!='AWAITING_INPUT':
                state = "BLOCKED"
            elif state in {"PAUSED","BLOCKED"}:
                state = "QUEUED"
        return {"task_id":task_id,"run_id":run[0] if run else None,"revision":task[1],"state":state,
            "individual_hold":bool(run and run[2]),"global_hold":global_hold,"blocking_reasons":list(dict.fromkeys(reasons))}

    def task(self,task_id):
        return self.writer.call(lambda db:self._snapshot(db,identifier(task_id)),transaction=False)

    def task_command(self,principal,task_id,body):
        task_id = identifier(task_id)
        body = validate("TaskCommand",body)
        def change(db):
            task = self._task(db,task_id)
            if task[1]!=body["expected_revision"]:
                raise DomainError("REVISION_CONFLICT")
            run = self._run(db,task_id)
            operation = body["operation"]
            if operation in {"start","restart"}:
                if (operation=="start" and run) or (operation=="restart" and (not run or run[1]!="STOPPED")):
                    raise DomainError("INVALID_STATE")
                run_id = str(uuid4())
                db.execute("INSERT INTO runs VALUES(?,?,?,'QUEUED',0,0,1,NULL)",(run_id,task_id,run[3]+1 if run else 1))
                db.execute('INSERT INTO run_progress(run_id) VALUES(?)',(run_id,))
            else:
                if not run or run[1] in TERMINAL:
                    raise DomainError("INVALID_STATE")
                if operation=="pause":
                    db.execute("UPDATE runs SET individual_hold=1,revision=revision+1 WHERE id=?",(run[0],))
                elif operation=="resume":
                    db.execute("UPDATE runs SET individual_hold=0,revision=revision+1 WHERE id=?",(run[0],))
                elif operation=="stop":
                    db.execute("UPDATE runs SET stop_requested=1,state='STOPPED',terminal_at=?,revision=revision+1 WHERE id=?",(self.stamp(),run[0]))
                    for (action_id,) in db.execute("SELECT id FROM actions WHERE run_id=? AND state IN('PREPARED','WAITING_AUTH','READY','DISPATCH_INTENT')",(run[0],)).fetchall():
                        self._cancel_unclaimed(db,action_id)
                    db.execute("UPDATE leases SET fenced=1 WHERE run_id=?",(run[0],))
            db.execute("UPDATE tasks SET revision=revision+1 WHERE id=?",(task_id,))
            snapshot = self._snapshot(db,task_id)
            self.event(db,"TASK_"+operation.upper(),"task",task_id,snapshot["revision"],{"state":snapshot["state"]})
            return self.receipt(task_id,snapshot["revision"],snapshot["state"],snapshot["blocking_reasons"])
        return self.command(principal,body["command_id"],["task_command",task_id,body],change)

    def global_command(self,principal,body):
        body = validate("GlobalCommand",body)
        def change(db):
            row = db.execute("SELECT global_hold,revision FROM execution_control WHERE id=1").fetchone()
            if row[1]!=body["expected_revision"]:
                raise DomainError("REVISION_CONFLICT")
            hold = int(body["operation"]!="resume_all")
            db.execute("UPDATE execution_control SET global_hold=?,revision=revision+1 WHERE id=1",(hold,))
            self.event(db,"EXECUTION_"+body["operation"].upper(),"execution",GLOBAL_ID,row[1]+1)
            return self.receipt(GLOBAL_ID,row[1]+1,"STOPPING" if body["operation"]=="quit" else "PAUSED" if hold else "RESUMED")
        return self.command(principal,body["command_id"],["global",body],change)

    def recover(self):
        def change(db):
            db.execute("UPDATE leases SET fenced=1")
            for action,application,kind in db.execute("SELECT id,application_id,kind FROM actions WHERE state IN('DISPATCH_INTENT','CLAIMED','DISPATCHED')").fetchall():
                db.execute("UPDATE actions SET state='UNCERTAIN',revision=revision+1 WHERE id=?",(action,))
                if kind=='submit_application':
                    db.execute("INSERT INTO submission_guards VALUES(?,?,'UNCERTAIN',1) ON CONFLICT(application_id) DO UPDATE SET reason=CASE WHEN reason IN('CONFIRMED','USER_REPORTED') THEN reason ELSE 'UNCERTAIN' END,revision=revision+1",(application,action))
                    db.execute("UPDATE applications SET effective_outcome=CASE WHEN effective_outcome IN('CONFIRMED','USER_REPORTED') THEN effective_outcome ELSE 'UNCERTAIN' END,revision=revision+1 WHERE id=?",(application,))
                db.execute("UPDATE reservations SET state='UNCERTAIN' WHERE action_id=? AND state='RESERVED'",(action,))
                self.event(db,"ACTION_RECOVERY_UNCERTAIN","action",action,db.execute("SELECT revision FROM actions WHERE id=?",(action,)).fetchone()[0])
            for run,task in db.execute("SELECT id,task_id FROM runs WHERE state='ACTIVE'").fetchall():
                db.execute("UPDATE runs SET state='BLOCKED',revision=revision+1 WHERE id=?",(run,))
                db.execute("INSERT OR IGNORE INTO run_blockers VALUES(?,'WORKER_UNAVAILABLE')",(run,))
                db.execute('UPDATE tasks SET revision=revision+1 WHERE id=?',(task,))
                self.event(db,'RUN_RECOVERY_BLOCKED','task',task,self._task(db,task)[1])
        with self.dispatch_lock:
            self.writer.call(change)
