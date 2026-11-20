import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'common'))
from evaluation import footprint,rectangle,clearance,world_goal,goal_errors


class EvaluationTests(unittest.TestCase):
    def test_known_rectangular_gap(self):
        self.assertAlmostEqual(clearance(rectangle(0,0,1,1),rectangle(2,0,1,1)),1.)

    def test_overlap_and_contact_distinguished(self):
        self.assertLess(clearance(rectangle(0,0,1,1),rectangle(.7,0,1,1)),0.)
        self.assertAlmostEqual(clearance(rectangle(0,0,1,1),rectangle(1,0,1,1)),0.)

    def test_rear_axle_body_offset_and_rotation(self):
        rear=footprint((0,0,0),True)
        self.assertAlmostEqual(min(x for x,y in rear),-.085)
        self.assertAlmostEqual(max(x for x,y in rear),.365)
        turned=footprint((0,0,math.pi/2),True)
        self.assertAlmostEqual(max(y for x,y in turned),.365)

    def test_symmetric_clearance_including_diagonal(self):
        a,b=footprint((.3,.2,.7)),rectangle(1,1,.2,.3)
        self.assertAlmostEqual(clearance(a,b),clearance(b,a))
        self.assertGreater(clearance(a,b),0.)

    def test_goal_transform_and_heading_wrap(self):
        self.assertEqual(world_goal((10.,4.,math.pi/2)),(11.,5.,math.pi/2))
        error=goal_errors((0.,0.,-math.pi+.02),(0.,0.,math.pi-.02))
        self.assertAlmostEqual(error['yaw_rad'],.04)


if __name__=='__main__': unittest.main()
