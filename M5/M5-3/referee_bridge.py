"""Protocol and countdown, independent of transport for contract testing."""
import time


class Referee:
    def __init__(self,execute):
        self.execute=execute; self.state='READY'; self.penalties=[]; self.started=None; self.remaining=180.; self.countdown_until=None; self.competition_active=False

    def command(self,command,user='referee',**args):
        command=command.upper()
        if command=='START':
            if self.state!='READY': raise ValueError('START requires READY')
            self.countdown_until=time.monotonic()+3.; self.state='COUNTDOWN'; self.competition_active=True
        elif command=='PAUSE':
            if self.state!='RUNNING': raise ValueError('PAUSE requires RUNNING')
            self.remaining=max(0,self.remaining-(time.monotonic()-self.started)); self.state='PAUSED'; self.execute('pause',user)
        elif command=='RESUME':
            if self.state!='PAUSED': raise ValueError('RESUME requires PAUSED')
            self.started=time.monotonic(); self.state='RUNNING'; self.execute('resume',user)
        elif command=='STOP':
            if self.state=='RUNNING': self.remaining=max(0,self.remaining-(time.monotonic()-self.started))
            self.state='STOPPED'; self.competition_active=False; self.execute('stop',user)
        elif command=='PENALTY':
            seconds=float(args.get('seconds',0))
            if seconds<0 or seconds>180: raise ValueError('Invalid penalty seconds')
            self.penalties.append(dict(ts_ns=time.time_ns(),seconds=seconds,reason=str(args.get('reason',''))))
            self.remaining=max(0,self.remaining-seconds)
        elif command!='SCORE_QUERY': raise ValueError('Unknown referee command: '+command)
        return self.snapshot()

    def tick(self):
        now=time.monotonic()
        if self.state=='COUNTDOWN' and now>=self.countdown_until:
            self.state='RUNNING'; self.started=now; self.execute('start','countdown')
        if self.state=='RUNNING' and self.remaining-(now-self.started)<=0:
            self.remaining=0; self.state='STOPPED'; self.competition_active=False; self.execute('stop','countdown_expired')

    def snapshot(self):
        remaining=max(0,self.remaining-(time.monotonic()-self.started)) if self.state=='RUNNING' else self.remaining
        countdown=max(0,self.countdown_until-time.monotonic()) if self.state=='COUNTDOWN' else 0
        return dict(state=self.state,remaining_s=remaining,start_countdown_s=countdown,penalties=self.penalties,competition_active=self.competition_active)
