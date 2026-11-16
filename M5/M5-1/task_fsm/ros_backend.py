"""ROS transport adapter; no success is invented when hardware is unavailable."""
import json
import math
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from sensor_interfaces.action import Grasp
from sensor_interfaces.srv import SpeakTTS as SpeakService
from std_msgs.msg import Bool,String


class RosBackend:
    def __init__(self):
        self.owns_context=not rclpy.ok()
        if self.owns_context: rclpy.init()
        self.node=Node('task_ros_adapter'); self.triggered=threading.Event(); self.targets={}
        self.node.create_subscription(Bool,'/referee/start_cmd',lambda m:self.triggered.set() if m.data else None,10)
        self.node.create_subscription(String,'/perception/targets',self.on_targets,10)
        self.nav=ActionClient(self.node,NavigateToPose,'/navigate_to_pose'); self.grasp=ActionClient(self.node,Grasp,'/manipulation/grasp')
        self.speak=self.node.create_client(SpeakService,'/tts/speak')
        self.executor=MultiThreadedExecutor(num_threads=2); self.executor.add_node(self.node)
        self.thread=threading.Thread(target=self.executor.spin,daemon=True); self.thread.start()

    def on_targets(self,message):
        try: self.targets=json.loads(message.data)
        except ValueError: self.node.get_logger().warning('Invalid targets JSON ignored')

    def wait(self,future,leaf):
        while not future.done() and leaf.ctx.checkpoint(leaf.cancelled): leaf.cancelled.wait(.01)
        return future.result() if future.done() else None

    def action(self,client,goal,leaf):
        while not client.wait_for_server(timeout_sec=.05):
            if not leaf.ctx.checkpoint(leaf.cancelled): return dict(success=False,reason='server unavailable/cancelled')
        future=client.send_goal_async(goal,feedback_callback=lambda f:leaf.progress(.5,feedback=str(f.feedback)))
        # If cancellation races acceptance, attach a callback so a late accepted goal is cancelled too.
        handle=self.wait(future,leaf)
        if handle is None:
            def cancel_late(f):
                if f.result() and f.result().accepted: f.result().cancel_goal_async()
            future.add_done_callback(cancel_late); return dict(success=False,cancelled=True)
        if not handle.accepted: return dict(success=False,reason='goal rejected')
        result=self.wait(handle.get_result_async(),leaf)
        if result is None: handle.cancel_goal_async(); return dict(success=False,cancelled=True)
        answer=dict(success=result.status==4,status=result.status)
        if hasattr(result.result,'object_pose_json'):
            answer['success']=answer['success'] and result.result.success
            answer['object_pose']=json.loads(result.result.object_pose_json or 'null')
        return answer

    def perform(self,kind,leaf):
        if kind=='trigger':
            while not self.triggered.is_set() and not leaf.ctx.data.get('triggered'):
                if not leaf.ctx.checkpoint(leaf.cancelled): return dict(success=False)
                leaf.cancelled.wait(.01)
            self.triggered.clear(); return dict(success=True)
        if kind=='detect': return dict(success=True,targets=self.targets.get('targets',[]))
        if kind=='navigate':
            pose=leaf.ctx.data[leaf.params['pose_from_context']] if 'pose_from_context' in leaf.params else leaf.params['pose']
            if not isinstance(pose,dict): pose=dict(zip(['x','y','yaw'],pose))
            goal=NavigateToPose.Goal(); goal.pose.header.frame_id=pose.get('frame','map'); goal.pose.header.stamp=self.node.get_clock().now().to_msg()
            goal.pose.pose.position.x=float(pose['x']); goal.pose.pose.position.y=float(pose['y'])
            goal.pose.pose.orientation.z=math.sin(pose.get('yaw',0)/2); goal.pose.pose.orientation.w=math.cos(pose.get('yaw',0)/2)
            return self.action(self.nav,goal,leaf)
        if kind=='grasp':
            goal=Grasp.Goal(); goal.pose_json=json.dumps(leaf.params.get('grasp_pose',leaf.ctx.data.get('target_pose'))); goal.grasp_type=leaf.params.get('grasp_type','top_down')
            return self.action(self.grasp,goal,leaf)
        while not self.speak.wait_for_service(timeout_sec=.05):
            if not leaf.ctx.checkpoint(leaf.cancelled): return dict(success=False)
        req=SpeakService.Request(); req.text=leaf.params['text']; result=self.wait(self.speak.call_async(req),leaf)
        return dict(success=bool(result and result.success))

    def close(self):
        self.executor.shutdown(timeout_sec=2); self.thread.join(2); self.node.destroy_node()
        if self.owns_context: rclpy.shutdown()
