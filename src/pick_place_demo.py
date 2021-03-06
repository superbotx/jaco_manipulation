#!/usr/bin/env python
import rospy
import rospkg

from moveit_interface import RobotPlanner, GripController
from grasp_planner import GQCNNPlanner
import numpy as np
import signal

from path_planner import PathPlanner

from autolab_core import YamlConfig
from spacial_location import Pose

# import perception

from sensor_msgs.msg import Image

class PickPlaceDemo:
    def __init__(self, grasp_planner, path_planner, grip_controller, camera, config):
        self.grasp_planner = grasp_planner
        self.path_planner = path_planner
        self.grip_controller = grip_controller

        self.config = config
        self.camera = camera

    def _plan_and_execute(self, location, pause_message=None):
        """ plan and execute a path to a location with optional paus message
        """
        print ("Planning and executing to: ", location)

        # self.path_planner.plan(location)
        # if pause_message:
        #     data = raw_input(pause_message)
        #     if data == 'q':
        #         return False
        # return self.path_planner.execute()
        # location.position.z = location.position.z -1
        # location_new = Pose([location.position.x-0.2, location.position.y, location.position.z-1], location.orientation, "root")
        # print(location_new)
        pose = path_planner.make_pose(location.position, location._orientation, "root")
        print("Pose: ", pose)
        joints = path_planner.get_ik(pose)
        print("Joints: ", joints)
        raw_input("Press Enter to move to position")
        plan = path_planner.plan_to_config(joints)
        return path_planner.execute_path(plan)

    def _get_bounding_box(self, object_name, color_image):
        """ Find the bounding box for the object
        params
        ---
        object_name: the string name of the object
        color_image: the color image for the object

        returns
        ---
        bounding_box: numpy array [minX, minY, maxX, maxY] in pixels around the image 
        on the depth image
        """
        return np.array([200,270,300,370]) 
        #return np.array([500,500,1000,800])

    def move_object(self, object_name):
        """ A somewhat ugly function which runs pick and place using the AR trackers
        """

        print("Starting pack and place demo.")
        color_image, depth_image, _ = self.camera.frames()
        
        bounding_box = self._get_bounding_box(object_name, color_image)
        print("trace starting")
        print(bounding_box)

        pregrasp_pose, grasp_pose = grasp_planner.get_grasp_plan(bounding_box, color_image, depth_image)
        print("Grasp plan completed.")
        print("Pre grasp pose: ", pregrasp_pose)
        print("Grasp pose: ", grasp_pose)
        
        self.grip_controller.grip("percent",[0,0,0])

        # home_grip_msg = "plan to grasp_pre_hardcode complete, anykey and enter to execute"
        # self._plan_and_execute("home_grip", pause_message=home_grip_msg)

        pregrasp_pose_msg = "Enter to execute pregrasp"
        self._plan_and_execute(pregrasp_pose)

        grasp_pose_msg = "Enter to execute grasp"
        self._plan_and_execute(grasp_pose)

        #grip object
        #raw_input("grip object? anykey to execute")
        self.grip_controller.grip("percent",[75,75,75])
        
        #target pre
        self._plan_and_execute("grasp_target_pre")

        #target location
        self._plan_and_execute("grasp_target")

        #release object
        #raw_input("release object? anykey to execute")
        self.grip_controller.grip("percent",[0,0,0])
        rospy.sleep(1)

        self._plan_and_execute("home_grip")

if __name__ == '__main__':
    print("Starting pick_place_demo")
    rospy.init_node("pick_place_demo", log_level=rospy.DEBUG)
    rospack = rospkg.RosPack()
    yaml_path = rospack.get_path('jaco_manipulation')

    config = YamlConfig(yaml_path + '/cfg/grasp_sim.yaml')

    # create rgbd sensor
    rospy.loginfo('Creating RGBD Sensor')
    sensor_cfg = config['sensor_cfg']
    sensor_type = sensor_cfg['type']
    print(sensor_type)

    import perception

    camera = perception.RgbdSensorFactory.sensor(sensor_type, sensor_cfg)
    camera.start()
    rospy.loginfo('Sensor Running')
    
    # setup safe termination
    def handler(signum, frame):
        rospy.loginfo('caught CTRL+C, exiting...')        
        # if camera is not None:
        #     # camera.stop()
        #TODO fix subscriber to be real
        if subscriber is not None and subscriber._started:
            subscriber.stop()            
        exit(0)
    signal.signal(signal.SIGINT, handler)

    frame = config['sensor_cfg']['frame']

    camera_intrinsics = camera.ir_intrinsics
    # 32-bit number in meters (each pixel)
    #camera_intrinsics = perception.CameraIntrinsics(frame, fx=365.46, fy=365.46, cx=254.9, cy=205.4, skew=0.0, height=424, width=512) #TODO set height and width with param 
    grasp_planner = GQCNNPlanner(camera_intrinsics, config)
    print("grasp planning done.")

    # path_planner = RobotPlanner()
    path_planner = PathPlanner()
    grip_controller = GripController()
    object_name = "cup"

    picker = PickPlaceDemo(grasp_planner, path_planner, grip_controller, camera, config)
    picker.move_object(object_name)

    rospy.spin()