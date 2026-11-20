"""A new-session grandchild must stop; an unrelated sibling must survive."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'common'))


@unittest.skipUnless(os.name=='posix' and Path('/proc').exists(),'Linux process ownership test')
class ProcessCleanupTests(unittest.TestCase):
    def test_new_session_child_and_unrelated_process(self):
        from process_cleanup import terminate_owned_tree,identity
        sleeper='import time; time.sleep(60)'
        unrelated=subprocess.Popen([sys.executable,'-c',sleeper],stderr=subprocess.DEVNULL)
        parent_code='import subprocess,sys,time; child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"],start_new_session=True); print(child.pid,flush=True); time.sleep(60)'
        parent=subprocess.Popen([sys.executable,'-c',parent_code],stdout=subprocess.PIPE,text=True,stderr=subprocess.DEVNULL)
        try:
            child_pid=int(parent.stdout.readline().strip())
            terminate_owned_tree(parent,grace=.5)
            self.assertIsNone(identity(child_pid))
            self.assertIsNotNone(parent.poll())
            self.assertIsNone(unrelated.poll())
        finally:
            if parent.poll() is None: terminate_owned_tree(parent,grace=.5)
            parent.stdout.close()
            if unrelated.poll() is None: unrelated.terminate()
            unrelated.wait(timeout=3)


if __name__=='__main__': unittest.main()
