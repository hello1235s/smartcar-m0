import argparse
import json
import time
from pathlib import Path
from task_fsm import Engine, TaskContext
from task_fsm.nodes import MockBackend


def log(event):
    colors = {'RUNNING': 32, 'SUCCESS': 34, 'FAILED': 31, 'SKIPPED': 33, 'RETRYING': 35}
    print('\033[%dm%s %s %s\033[0m' % (colors.get(event['status'], 37), event['name'], event['status'], event.get('error') or ''), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('yaml')
    parser.add_argument('--backend', choices=['mock', 'ros'], default='mock')
    parser.add_argument('--deadline', type=float, default=180)
    parser.add_argument('--out', default='task_report.json')
    args = parser.parse_args()
    if args.backend == 'ros':
        from task_fsm.ros_backend import RosBackend
        backend = RosBackend()
    else:
        backend = MockBackend()
    ctx = TaskContext(task_id=time.strftime('run_%Y%m%d_%H%M%S'), deadline=time.monotonic()+args.deadline,
                      metadata={'backend': backend, 'backend_name': args.backend, 'on_event': log})
    try:
        report = Engine(args.yaml, ctx).run()
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return 0 if report['result'] == 'SUCCESS' else 1
    except (ValueError, OSError) as error:
        print('任务配置错误：'+str(error))
        return 2
    except KeyboardInterrupt:
        ctx.abort()
        return 130
    finally:
        if hasattr(backend, 'close'):
            backend.close()


if __name__ == '__main__':
    raise SystemExit(main())
